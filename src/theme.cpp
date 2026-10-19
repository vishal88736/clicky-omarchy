// Theme behavior follows the Omarchy app templates (MIT, David Heinemeier Hansson).
#include "theme.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
Theme::Theme(QObject *parent):QObject(parent){
    connect(&m_watch,&QFileSystemWatcher::fileChanged,this,[this]{reload();});
    connect(&m_watch,&QFileSystemWatcher::directoryChanged,this,[this]{reload();});
    connect(&m_poll,&QTimer::timeout,this,[this]{reload();});m_poll.start(3000);
    m_timeout.setSingleShot(true);m_timeout.setInterval(700);
    connect(&m_timeout,&QTimer::timeout,&m_hypr,&QProcess::kill);
    connect(&m_hypr,&QProcess::finished,this,[this](int code,QProcess::ExitStatus){
        m_timeout.stop();const auto n=QJsonDocument::fromJson(m_hypr.readAllStandardOutput()).object().value("int");
        if(!code&&n.isDouble()&&n.toInt()!=m_radius){m_radius=n.toInt();emit changed();}
    });reload();
}
void Theme::reload(){
    const auto base=qEnvironmentVariable("CLICKY_THEME_DIR",QDir::homePath()+"/.local/state/omarchy/current");
    const auto file=base+"/theme/colors.toml";
    for(const auto &p:QStringList{base,base+"/theme",file})if(QFileInfo::exists(p)&&!m_watch.files().contains(p)&&!m_watch.directories().contains(p))m_watch.addPath(p);
    QFile f(file);QString value="#FFD60A";
    if(f.open(QIODevice::ReadOnly)){
        auto match=QRegularExpression("^\\s*accent\\s*=\\s*[\"'](#[0-9A-Fa-f]{6})[\"']",QRegularExpression::MultilineOption).match(QString::fromUtf8(f.readAll()));
        if(match.hasMatch())value=match.captured(1);
    }
    if(value!=m_accent){m_accent=value;emit changed();}
    if(qEnvironmentVariable("QT_QPA_PLATFORM")!="offscreen"&&!qEnvironmentVariableIsEmpty("HYPRLAND_INSTANCE_SIGNATURE")&&m_hypr.state()==QProcess::NotRunning){
        m_hypr.start("hyprctl",{"-j","getoption","decoration:rounding"});m_timeout.start();
    }
}
