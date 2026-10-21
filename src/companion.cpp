#include "companion.h"
#include <LayerShellQt/Window>
#include <QGuiApplication>
#include <QScreen>
#include <QQmlContext>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>
#include <QSettings>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QQuickItem>
#include <cmath>

QString Companion::preferences()const{
    auto root=qEnvironmentVariable("CLICKY_CONFIG_HOME");
    if(root.isEmpty())root=QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation)+"/clicky";
    return root+"/buddy.ini";
}
Companion::Companion(QObject *parent):QObject(parent){
    m_enabled=QSettings(preferences(),QSettings::IniFormat).value("enabled",true).toBool();
    m_poll.setInterval(50);m_deadline.setInterval(500);m_deadline.setSingleShot(true);
    m_captionTimer.setSingleShot(true);m_guideTimer.setSingleShot(true);
    connect(&m_poll,&QTimer::timeout,this,&Companion::poll);
    connect(&m_socket,&QLocalSocket::errorOccurred,this,[this](QLocalSocket::LocalSocketError){
        m_deadline.stop();if(m_available){m_available=false;emit availableChanged();visibility();}
    });
    connect(&m_deadline,&QTimer::timeout,this,[this]{m_socket.abort();if(m_available){m_available=false;emit availableChanged();visibility();}});
    connect(&m_socket,&QLocalSocket::connected,this,[this]{m_reply.clear();m_socket.write("j/cursorpos");});
    connect(&m_socket,&QLocalSocket::readyRead,this,[this]{
        m_reply+=m_socket.readAll();if(m_reply.size()>4096){m_socket.abort();return;}
        QJsonParseError e;const auto doc=QJsonDocument::fromJson(m_reply,&e);
        if(e.error!=QJsonParseError::NoError || !doc.isObject())return;
        const auto p=doc.object();if(!p.value("x").isDouble()||!p.value("y").isDouble())return;
        const QPointF point(p["x"].toDouble(),p["y"].toDouble());
        if(point!=m_position){m_position=point;emit positionChanged();}
        if(!m_available){m_available=true;emit availableChanged();visibility();}
        m_deadline.stop();m_socket.abort();
    });
    connect(&m_captionTimer,&QTimer::timeout,this,[this]{m_caption.clear();emit captionChanged();});
    connect(&m_guideTimer,&QTimer::timeout,this,[this]{m_guiding=false;emit guidanceChanged();});
}
Companion::~Companion(){qDeleteAll(m_windows);}
void Companion::start(QQmlEngine *engine){
    m_engine=engine;
    if(QGuiApplication::platformName()!="wayland")return;
    connect(qGuiApp,&QGuiApplication::screenAdded,this,[this](QScreen*){rebuild();});
    connect(qGuiApp,&QGuiApplication::screenRemoved,this,[this](QScreen*){QTimer::singleShot(0,this,&Companion::rebuild);});
    rebuild();m_poll.start();poll();
}
void Companion::rebuild(){
    qDeleteAll(m_windows);m_windows.clear();
    for(auto *screen:QGuiApplication::screens()){
        auto *window=new QQuickView(m_engine,nullptr);
        window->setScreen(screen);window->setColor(Qt::transparent);
        window->setFlags(Qt::FramelessWindowHint|Qt::WindowStaysOnTopHint|Qt::WindowTransparentForInput|Qt::WindowDoesNotAcceptFocus);
        auto *layer=LayerShellQt::Window::get(window);
        layer->setScope("clicky-buddy");layer->setScreen(screen);
        layer->setLayer(LayerShellQt::Window::LayerOverlay);
        layer->setAnchors(LayerShellQt::Window::Anchors::fromInt(15));
        layer->setExclusiveZone(-1);layer->setKeyboardInteractivity(LayerShellQt::Window::KeyboardInteractivityNone);layer->setActivateOnShow(false);
        window->setResizeMode(QQuickView::SizeRootObjectToView);window->resize(screen->geometry().size());
        window->setInitialProperties({{"originX",screen->geometry().x()},{"originY",screen->geometry().y()}});
        connect(screen,&QScreen::geometryChanged,window,[window,screen]{
            window->resize(screen->geometry().size());
            if(window->rootObject()){window->rootObject()->setProperty("originX",screen->geometry().x());window->rootObject()->setProperty("originY",screen->geometry().y());}
        });
        window->setSource(QUrl("qrc:/BuddyOverlay.qml"));m_windows.append(window);
    }
    visibility();
}
void Companion::visibility(){for(auto *w:m_windows)w->setVisible(m_enabled&&m_available&&!m_suspended);}
void Companion::setEnabled(bool value){
    if(m_enabled==value)return;
    m_enabled=value;QDir().mkpath(QFileInfo(preferences()).absolutePath());
    QSettings s(preferences(),QSettings::IniFormat);s.setValue("enabled",value);s.sync();
    QFile::setPermissions(preferences(),QFile::ReadOwner|QFile::WriteOwner);
    visibility();emit enabledChanged();
}
void Companion::suspend(bool value){m_suspended=value;visibility();}
void Companion::poll(){
    if(!m_enabled||m_suspended||m_socket.state()!=QLocalSocket::UnconnectedState)return;
    const auto instance=qEnvironmentVariable("HYPRLAND_INSTANCE_SIGNATURE");
    if(instance.isEmpty())return;
    const auto path=QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation)+"/hypr/"+instance+"/.socket.sock";
    m_socket.connectToServer(path);m_deadline.start();
}
void Companion::say(const QString &text,int milliseconds){m_caption=text.left(500);emit captionChanged();m_captionTimer.start(qBound(1000,milliseconds,30000));}
void Companion::guide(qreal x,qreal y,const QString &label){
    if(!std::isfinite(x)||!std::isfinite(y))return;
    if(!QGuiApplication::screenAt(QPoint(qRound(x),qRound(y))))return;
    m_target=QPointF(x,y);m_guiding=true;emit guidanceChanged();say(label,7000);m_guideTimer.start(6500);
}
void Companion::clear(){m_guideTimer.stop();m_captionTimer.stop();m_guiding=false;m_caption.clear();emit guidanceChanged();emit captionChanged();}
void Companion::tour(){
    auto *screen=QGuiApplication::screenAt(m_position.toPoint());if(!screen)screen=QGuiApplication::primaryScreen();if(!screen)return;
    const auto g=screen->geometry();guide(g.x()+g.width()*.6,g.y()+g.height()*.38,tr("I can point things out. Your real pointer stays yours."));
    QTimer::singleShot(6800,this,[this]{say(tr("Back by your side. Open the prompt with Super + Ctrl + ;"),9000);});
}
