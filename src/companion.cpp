#include "companion.h"
#include <LayerShellQt/Window>
#include <QGuiApplication>
#include <QScreen>
#include <QQuickItem>
#include <QStandardPaths>
#include <QSettings>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <cmath>

QString Companion::preferences()const{
    auto root=qEnvironmentVariable("CLICKY_CONFIG_HOME");
    if(root.isEmpty())root=QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation)+"/clicky";
    return root+"/buddy.ini";
}
Companion::Companion(QObject *parent):QObject(parent){
    // Existing disabled preference is retained. Fresh installations have no overlay.
    m_enabled=QSettings(preferences(),QSettings::IniFormat).value("enabled",false).toBool();
    m_guideTimer.setSingleShot(true);connect(&m_guideTimer,&QTimer::timeout,this,&Companion::clear);
}
Companion::~Companion(){qDeleteAll(m_windows);}
void Companion::start(QQmlEngine *engine){
    m_engine=engine;m_available=QGuiApplication::platformName()=="wayland";emit availableChanged();
    if(!m_available)return;
    connect(qGuiApp,&QGuiApplication::screenAdded,this,[this](QScreen*){if(m_guiding)rebuild();});
    connect(qGuiApp,&QGuiApplication::screenRemoved,this,[this](QScreen*){QTimer::singleShot(0,this,[this]{if(m_guiding)rebuild();});});
    // Deliberately do not create surfaces, read cursor IPC, or start a poll timer.
}
void Companion::rebuild(){
    qDeleteAll(m_windows);m_windows.clear();
    if(!m_available||!m_engine||!m_guiding)return;
    for(auto *screen:QGuiApplication::screens()){
        auto *window=new QQuickView(m_engine,nullptr);window->setScreen(screen);window->setColor(Qt::transparent);
        window->setFlags(Qt::FramelessWindowHint|Qt::WindowStaysOnTopHint|Qt::WindowTransparentForInput|Qt::WindowDoesNotAcceptFocus);
        auto *layer=LayerShellQt::Window::get(window);layer->setScope("clicky-guidance");layer->setScreen(screen);
        layer->setLayer(LayerShellQt::Window::LayerOverlay);layer->setAnchors(LayerShellQt::Window::Anchors::fromInt(15));
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
void Companion::visibility(){for(auto *w:m_windows)w->setVisible(m_enabled&&m_guiding&&!m_suspended);}
void Companion::setEnabled(bool value){
    if(m_enabled==value)return;
    m_enabled=value;if(!value)clear();QDir().mkpath(QFileInfo(preferences()).absolutePath());
    QSettings s(preferences(),QSettings::IniFormat);s.setValue("enabled",value);s.sync();
    QFile::setPermissions(preferences(),QFile::ReadOwner|QFile::WriteOwner);visibility();emit enabledChanged();
}
void Companion::suspend(bool value){m_suspended=value;visibility();}
void Companion::say(const QString &text,int milliseconds){
    Q_UNUSED(milliseconds);
    // A response alone never opens an overlay. Full responses stay in the HUD.
    if(m_guiding){m_caption=text.left(500);emit captionChanged();}
}
void Companion::guide(qreal x,qreal y,const QString &label){
    if(!m_enabled||!std::isfinite(x)||!std::isfinite(y))return;
    if(!QGuiApplication::screenAt(QPoint(qRound(x),qRound(y))))return;
    m_target=QPointF(x,y);m_caption=label.left(500);m_guiding=true;emit guidanceChanged();emit captionChanged();
    if(m_windows.isEmpty())rebuild();else visibility();m_guideTimer.start(6500);
}
void Companion::clear(){m_guideTimer.stop();m_guiding=false;m_caption.clear();visibility();emit guidanceChanged();emit captionChanged();}
void Companion::tour(){
    if(!m_enabled)return;
    auto *screen=QGuiApplication::primaryScreen();if(!screen)return;
    const auto g=screen->geometry();guide(g.x()+g.width()*.6,g.y()+g.height()*.38,tr("A temporary visual hint. Nothing follows your pointer."));
}
