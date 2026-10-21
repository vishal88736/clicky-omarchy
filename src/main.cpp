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
#include <QQuickView>
#include <QQuickItem>
#include <QStandardPaths>
#include <QTimer>
#include <QScreen>
#include <csignal>
#include <cstdio>
#include "backend.h"
#include "theme.h"
#include "translator.h"
#include "companion.h"

static volatile std::sig_atomic_t stopping=0;
static void stopSignal(int){stopping=1;}
static QQuickItem *namedItem(QQuickItem *root,const QString &name){
    if(root->objectName()==name)return root;
    for(auto *child:root->childItems())if(auto *item=namedItem(child,name))return item;
    return nullptr;
}
int main(int argc,char **argv){
    QGuiApplication app(argc,argv);app.setApplicationName("clicky");app.setApplicationVersion("0.2.0");app.setDesktopFileName("clicky");app.setQuitOnLastWindowClosed(false);
    const auto args=app.arguments();const QString verb=args.size()>1?args[1]:"open";
    if(!QStringList{"open","toggle","hide","stop","status","info","tour","buddy","guides","--smoke"}.contains(verb)){fprintf(stderr,"Usage: clicky [open|toggle|hide|status|info|stop|tour|guides|--smoke image.png]\n");return 1;}
    QString runtime=qEnvironmentVariable("CLICKY_RUNTIME_HOME");
    if(runtime.isEmpty())runtime=QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation)+"/clicky";
    if(QFileInfo(runtime).isSymLink()){fprintf(stderr,"Refusing symlink runtime directory\n");return 1;}
    QDir().mkpath(runtime);QFile::setPermissions(runtime,QFile::ReadOwner|QFile::WriteOwner|QFile::ExeOwner);
    const auto socketPath=runtime+"/control";
    QLocalSocket existing;existing.connectToServer(socketPath);
    if(existing.waitForConnected(400)){
        existing.write(verb.toUtf8()+'\n');existing.waitForBytesWritten(500);existing.waitForReadyRead(600);
        if(verb=="status"||verb=="info"){const auto reply=existing.readAll();fwrite(reply.constData(),1,size_t(reply.size()),stdout);}
        return 0;
    }
    if(verb=="hide"||verb=="stop")return 0;
    if(verb=="status"||verb=="info"){puts("stopped");return 1;}
    QLockFile lock(runtime+"/instance.lock");lock.setStaleLockTime(0);
    if(!lock.tryLock(1000)){fprintf(stderr,"Another Clicky instance is starting\n");return 1;}
    QLocalServer::removeServer(socketPath);QLocalServer server;server.setSocketOptions(QLocalServer::UserAccessOption);
    if(!server.listen(socketPath)){fprintf(stderr,"Cannot open private control socket\n");return 1;}
    QQuickStyle::setStyle("Material");Translator translator;app.installTranslator(&translator);Theme theme;Backend backend;
    QQmlApplicationEngine engine;Companion companion;QObject::connect(&translator,&Translator::changed,&engine,&QQmlEngine::retranslate);
    engine.rootContext()->setContextProperty("backend",&backend);engine.rootContext()->setContextProperty("theme",&theme);engine.rootContext()->setContextProperty("translator",&translator);
    engine.rootContext()->setContextProperty("companion",&companion);
    engine.load(QUrl("qrc:/Main.qml"));if(engine.rootObjects().isEmpty())return 1;
    auto *window=qobject_cast<QQuickWindow*>(engine.rootObjects().first());
    if(auto *screen=app.screenAt(QCursor::pos());screen && qEnvironmentVariable("QT_QPA_PLATFORM")!="offscreen"){
        window->setScreen(screen);const auto g=screen->availableGeometry();
        window->setPosition(g.center()-QPoint(window->width()/2,window->height()/2));
    }
    companion.start(&engine);
    auto show=[window,&companion]{
        companion.suspend(false);
        window->show();window->raise();window->requestActivate();
        if(qEnvironmentVariable("QT_QPA_PLATFORM")!="offscreen")QTimer::singleShot(80,window,[]{
            QProcess::startDetached("hyprctl",{"dispatch","hl.dsp.focus({ window = \"class:^clicky$\" })"});
        });
    };
    QObject::connect(&backend,&Backend::showRequested,&app,show);QObject::connect(&backend,&Backend::hideRequested,&app,[&]{companion.suspend(true);window->hide();});
    QObject::connect(&backend,&Backend::workerEvent,&app,[&](const QVariantMap &v){
        if(v.value("event")=="guidance")companion.guide(v.value("x").toDouble(),v.value("y").toDouble(),v.value("label").toString());
        else if(v.value("event")=="answer")companion.say(v.value("text").toString(),20000);
        else if(v.value("event")=="approval")show();
    });
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
                else if(cmd=="tour")companion.tour();
                else if(cmd=="buddy"||cmd=="guides")companion.setEnabled(!companion.enabled());
                if(cmd=="info"){
                    QPointF button;
                    if(auto *item=namedItem(window->contentItem(),"historyToggle"))button=item->mapToScene(QPointF(item->width()/2,item->height()/2));
                    client->write(QJsonDocument::fromVariant(QVariantMap{{"visible",window->isVisible()},{"width",window->width()},{"height",window->height()},{"history_button_x",button.x()},{"history_button_y",button.y()},{"guides",companion.enabled()},{"following",false},{"available",companion.available()},{"guiding",companion.guiding()},{"target_x",companion.target().x()},{"target_y",companion.target().y()}}).toJson(QJsonDocument::Compact)+'\n');
                }
                else client->write(window->isVisible()?"visible\n":"hidden\n");
                client->flush();client->disconnectFromServer();
            });
            QTimer::singleShot(2000,client,[client]{client->disconnectFromServer();});
        }
    });
    std::signal(SIGTERM,stopSignal);std::signal(SIGINT,stopSignal);QTimer signalPoll;signalPoll.start(100);
    QObject::connect(&signalPoll,&QTimer::timeout,&app,[&]{if(stopping)app.exit(0);});
    QObject::connect(&app,&QCoreApplication::aboutToQuit,&app,[&]{
        // Flush a draft even if quit arrives before its debounce timer fires.
        QMetaObject::invokeMethod(window,"flushDraft");backend.shutdown();
    });
    if(verb=="--smoke"){
        if(args.value(3)=="buddy"){
            window->hide();QQuickView preview(&engine,nullptr);preview.setColor(QColor("#171e19"));preview.setResizeMode(QQuickView::SizeRootObjectToView);preview.resize(640,260);
            preview.setSource(QUrl("qrc:/BuddyOverlay.qml"));companion.setEnabled(true);companion.guide(105,100,"Hey, I'm Clicky. Right here when you need a hand.");preview.show();
            QTimer::singleShot(1800,&app,[&]{app.exit(preview.grabWindow().save(args.value(2))?0:1);});
            return app.exec();
        }
        if(!args.value(3).isEmpty())QTimer::singleShot(2200,&app,[&]{
            if(args[3]=="library")window->setProperty("libraryOpen",true);
            else if(auto *panel=window->findChild<QObject*>(args[3]))QMetaObject::invokeMethod(panel,"open");
        });
        show();QTimer::singleShot(3500,&app,[&]{const bool ok=window->grabWindow().save(args.value(2));app.exit(ok?0:1);});
    }else if(verb=="tour"){companion.tour();}
    else if(verb=="buddy"||verb=="guides"){companion.setEnabled(!companion.enabled());}
    else if(!args.contains("--background"))show();
    return app.exec();
}
