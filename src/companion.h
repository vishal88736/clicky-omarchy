#pragma once
#include <QObject>
#include <QPointF>
#include <QQuickView>
#include <QLocalSocket>
#include <QTimer>
class QQmlEngine;
class Companion : public QObject {
    Q_OBJECT
    Q_PROPERTY(QPointF position READ position NOTIFY positionChanged)
    Q_PROPERTY(bool enabled READ enabled WRITE setEnabled NOTIFY enabledChanged)
    Q_PROPERTY(bool available READ available NOTIFY availableChanged)
    Q_PROPERTY(bool guiding READ guiding NOTIFY guidanceChanged)
    Q_PROPERTY(QPointF target READ target NOTIFY guidanceChanged)
    Q_PROPERTY(QString caption READ caption NOTIFY captionChanged)
public:
    explicit Companion(QObject *parent=nullptr);
    ~Companion() override;
    void start(QQmlEngine *engine);
    QPointF position()const{return m_position;}
    QPointF target()const{return m_target;}
    bool enabled()const{return m_enabled;}
    bool available()const{return m_available;}
    bool guiding()const{return m_guiding;}
    QString caption()const{return m_caption;}
    void setEnabled(bool enabled);
    void suspend(bool value);
    Q_INVOKABLE void say(const QString &text,int milliseconds=10000);
    Q_INVOKABLE void guide(qreal x,qreal y,const QString &label);
    Q_INVOKABLE void clear();
    Q_INVOKABLE void tour();
signals:
    void positionChanged();
    void enabledChanged();
    void availableChanged();
    void guidanceChanged();
    void captionChanged();
private:
    void poll();
    void rebuild();
    void visibility();
    QString preferences()const;
    QQmlEngine *m_engine=nullptr;
    QList<QQuickView*> m_windows;
    QLocalSocket m_socket;
    QByteArray m_reply;
    QTimer m_poll,m_deadline,m_captionTimer,m_guideTimer;
    QPointF m_position,m_target;
    QString m_caption;
    bool m_enabled=true,m_available=false,m_guiding=false,m_suspended=false;
};
