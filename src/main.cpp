#include <QGuiApplication>
#include <QDir>
#include <QFileInfo>
#include <QFile>
#include <QCursor>
#include <QJsonDocument>
#include <QLocalServer>
#include <QLocalSocket>
#include <QLockFile>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QQuickWindow>
#include <QStandardPaths>
#include <QTimer>
#include <QScreen>
#include <csignal>
#include <cstdio>
#include "backend.h"
#include "theme.h"
#include "translator.h"

static volatile std::sig_atomic_t stopping=0;
static void stopSignal(int){stopping=1;}
int main(int argc,char **argv){
    QGuiApplication app(argc,argv);app.setApplicationName("clicky");app.setApplicationVersion("0.1.0");app.setDesktopFileName("clicky");app.setQuitOnLastWindowClosed(false);
    const auto args=app.arguments();const QString verb=args.size()>1?args[1]:"open";
    if(!QStringList{"open","toggle","hide","stop","status","--smoke"}.contains(verb)){fprintf(stderr,"Usage: clicky [open|toggle|hide|status|stop|--smoke image.png]\n");return 1;}
    QString runtime=qEnvironmentVariable("CLICKY_RUNTIME_HOME");
    if(runtime.isEmpty())runtime=QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation)+"/clicky";
    if(QFileInfo(runtime).isSymLink()){fprintf(stderr,"Refusing symlink runtime directory\n");return 1;}
    QDir().mkpath(runtime);QFile::setPermissions(runtime,QFile::ReadOwner|QFile::WriteOwner|QFile::ExeOwner);
    const auto socketPath=runtime+"/control";
    QLocalSocket existing;existing.connectToServer(socketPath);
    if(existing.waitForConnected(400)){
        existing.write(verb.toUtf8()+'\n');existing.waitForBytesWritten(500);existing.waitForReadyRead(600);
        if(verb=="status"){const auto reply=existing.readAll();fwrite(reply.constData(),1,size_t(reply.size()),stdout);}
        return 0;
    }
    if(verb=="hide"||verb=="stop")return 0;
    if(verb=="status"){puts("stopped");return 1;}
    QLockFile lock(runtime+"/instance.lock");lock.setStaleLockTime(0);
    if(!lock.tryLock(1000)){fprintf(stderr,"Another Clicky instance is starting\n");return 1;}
    QLocalServer::removeServer(socketPath);QLocalServer server;server.setSocketOptions(QLocalServer::UserAccessOption);
    if(!server.listen(socketPath)){fprintf(stderr,"Cannot open private control socket\n");return 1;}
    QQuickStyle::setStyle("Material");Translator translator;app.installTranslator(&translator);Theme theme;Backend backend;
    QQmlApplicationEngine engine;QObject::connect(&translator,&Translator::changed,&engine,&QQmlEngine::retranslate);
    engine.rootContext()->setContextProperty("backend",&backend);engine.rootContext()->setContextProperty("theme",&theme);engine.rootContext()->setContextProperty("translator",&translator);
    engine.load(QUrl("qrc:/Main.qml"));if(engine.rootObjects().isEmpty())return 1;
    auto *window=qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    if(auto *screen=app.screenAt(QCursor::pos());screen && qEnvironmentVariable("QT_QPA_PLATFORM")!="offscreen"){
        window->setScreen(screen);const auto g=screen->availableGeometry();window->resize(qMin(1120,g.width()-40),qMin(780,g.height()-40));
        window->setPosition(g.center()-QPoint(window->width()/2,window->height()/2));
    }
    auto show=[window]{
        window->show();window->raise();window->requestActivate();
        if(qEnvironmentVariable("QT_QPA_PLATFORM")!="offscreen")QTimer::singleShot(80,window,[]{
            QProcess::startDetached("hyprctl",{"dispatch","hl.dsp.focus({ window = \"class:^clicky$\" })"});
        });
    };
    QObject::connect(&backend,&Backend::showRequested,&app,show);QObject::connect(&backend,&Backend::hideRequested,window,&QWindow::hide);
    QObject::connect(&backend,&Backend::quitRequested,&app,[&]{app.exit(0);});
    QObject::connect(&server,&QLocalServer::newConnection,&app,[&]{
        while(auto *client=server.nextPendingConnection()){
            QObject::connect(client,&QLocalSocket::disconnected,client,&QObject::deleteLater);
            QObject::connect(client,&QLocalSocket::readyRead,&app,[&,client]{
                if(client->bytesAvailable()>100){client->abort();return;}
                if(!client->canReadLine())return;
                const auto cmd=client->readLine().trimmed();
                if(cmd=="stop")app.exit(0);else if(cmd=="hide")window->hide();else if(cmd=="open")show();
                else if(cmd=="toggle"){if(window->isVisible())window->hide();else show();}
                client->write(window->isVisible()?"visible\n":"hidden\n");client->flush();client->disconnectFromServer();
            });
            QTimer::singleShot(2000,client,[client]{client->disconnectFromServer();});
        }
    });
    std::signal(SIGTERM,stopSignal);std::signal(SIGINT,stopSignal);QTimer signalPoll;signalPoll.start(100);
    QObject::connect(&signalPoll,&QTimer::timeout,&app,[&]{if(stopping)app.exit(0);});
    QObject::connect(&app,&QCoreApplication::aboutToQuit,&backend,&Backend::shutdown);
    if(verb=="--smoke"){
        if(!args.value(3).isEmpty())QTimer::singleShot(2200,&app,[&]{if(auto *panel=window->findChild<QObject*>(args[3]))QMetaObject::invokeMethod(panel,"open");});
        show();QTimer::singleShot(3500,&app,[&]{const bool ok=window->grabWindow().save(args.value(2));app.exit(ok?0:1);});
    }else if(!args.contains("--background"))show();
    return app.exec();
}
