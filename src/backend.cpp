#include "backend.h"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcessEnvironment>
#include <QTimer>

Backend::Backend(QObject *parent):QObject(parent) {
    QString project=qEnvironmentVariable("CLICKY_PROJECT_HOME");
    if (project.isEmpty()) project=QStringLiteral(CLICKY_PROJECT);
    const QString python=project+"/.venv/bin/python";
    if (!QFileInfo::exists(python)) {
        QTimer::singleShot(0,this,[this]{fail(tr("Project dependencies are missing. Run bin/build."));});
        return;
    }
    m_worker.setWorkingDirectory(project);
    auto env=QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONUNBUFFERED","1");env.insert("PYTHONDONTWRITEBYTECODE","1");
    m_worker.setProcessEnvironment(env);
    connect(&m_worker,&QProcess::readyReadStandardOutput,this,&Backend::consume);
    // Worker stderr is deliberately not echoed: third-party SDKs can include payloads.
    connect(&m_worker,&QProcess::readyReadStandardError,this,[this]{m_worker.readAllStandardError();});
    connect(&m_worker,&QProcess::errorOccurred,this,[this](QProcess::ProcessError){if(!m_stopping) fail(tr("Assistant worker could not start. Check the project environment."));});
    connect(&m_worker,&QProcess::finished,this,[this](int code,QProcess::ExitStatus){
        if(!m_stopping) fail(tr("Assistant worker stopped (exit %1). Restart Clicky; history is saved.").arg(code));
        m_busy=false;emit busyChanged();
    });
    m_worker.start(python,{"-m","clicky.worker"});
    const auto engines=QTextToSpeech::availableEngines();
    if (!engines.isEmpty() && qEnvironmentVariable("CLICKY_DISABLE_TTS")!="1") {
        m_speech=new QTextToSpeech(engines.first(),this);
        if (m_speech->availableVoices().isEmpty()) m_speechStatus=tr("No local speech voice installed");
        else m_speechStatus=tr("Local speech: %1").arg(engines.first());
        connect(m_speech,&QTextToSpeech::errorOccurred,this,[this](QTextToSpeech::ErrorReason,const QString &){fail(tr("Local speech engine failed. Check installed voices and audio output."));});
    } else m_speechStatus=tr("No local speech engine installed");
}
Backend::~Backend(){ shutdown(); }
void Backend::fail(const QString &message){m_error=message;emit errorChanged();}
void Backend::dismissError(){m_error.clear();emit errorChanged();}
void Backend::send(const QVariantMap &message){
    if(message.value("cmd")=="cancel") mute();
    if(m_worker.state()!=QProcess::Running){fail(tr("Worker is unavailable. Restart Clicky."));return;}
    const auto bytes=QJsonDocument(QJsonObject::fromVariantMap(message)).toJson(QJsonDocument::Compact);
    if(bytes.size()>900000){fail(tr("Request is too large."));return;}
    m_worker.write(bytes+'\n');
}
void Backend::consume(){
    m_buffer+=m_worker.readAllStandardOutput();
    if(m_buffer.size()>4000000){m_buffer.clear();fail(tr("Worker message exceeded the size limit."));return;}
    int end;
    while((end=m_buffer.indexOf('\n'))>=0){
        const auto line=m_buffer.left(end);m_buffer.remove(0,end+1);
        QJsonParseError parse;
        const auto obj=QJsonDocument::fromJson(line,&parse).object();
        if(parse.error!=QJsonParseError::NoError){fail(tr("Invalid worker response."));continue;}
        const auto type=obj.value("event").toString();
        if(type=="state"){m_state=obj.toVariantMap();m_busy=obj.value("busy").toBool();emit stateChanged();emit busyChanged();}
        else if(type=="mcp"){m_servers=obj.value("servers").toArray().toVariantList();emit serversChanged();}
        else if(type=="error"){fail(obj.value("message").toString());}
        else if(type=="busy"){m_busy=obj.value("value").toBool();emit busyChanged();}
        else if(type=="voice"){m_voiceState=obj.value("state").toString();emit voiceChanged();}
        else if(type=="restore_window") emit showRequested();
        else if(type=="delta") {
            const auto cid=obj.value("conversation").toString();
            if(cid==m_state.value("conversation").toString()){
                auto messages=m_state.value("messages").toList();bool found=false;
                for(auto &v:messages){auto m=v.toMap();if(m.value("id").toInt()==obj.value("message").toInt()){
                    m["content"]=m.value("content").toString()+obj.value("text").toString();v=m;found=true;break;}}
                if(!found) send({{"cmd","state"}});
                else {m_state["messages"]=messages;emit stateChanged();}
            }
        }
        emit workerEvent(obj.toVariantMap());
    }
}
void Backend::capture(bool region){emit hideRequested();send({{"cmd","capture"},{"region",region}});}
void Backend::windowContext(){emit hideRequested();send({{"cmd","window_context"}});}
void Backend::speak(const QString &text){
    if(!m_speech || m_speech->availableVoices().isEmpty()){fail(m_speechStatus);return;}
    m_speech->say(text.left(6000));
}
void Backend::mute(){if(m_speech)m_speech->stop();}
void Backend::shutdown(){
    if(m_stopping)return;
    m_stopping=true;mute();
    if(m_worker.state()!=QProcess::NotRunning){
        m_worker.write("{\"cmd\":\"quit\"}\n");m_worker.closeWriteChannel();
        if(!m_worker.waitForFinished(4000)){m_worker.terminate();if(!m_worker.waitForFinished(1000)){m_worker.kill();m_worker.waitForFinished(1000);}}
    }
}
