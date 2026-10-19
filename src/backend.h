#pragma once
#include <QObject>
#include <QProcess>
#include <QVariantMap>
#include <QTextToSpeech>

class Backend : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantMap state READ state NOTIFY stateChanged)
    Q_PROPERTY(QVariantList servers READ servers NOTIFY serversChanged)
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)
    Q_PROPERTY(QString voiceState READ voiceState NOTIFY voiceChanged)
    Q_PROPERTY(QString speechStatus READ speechStatus NOTIFY speechChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
public:
    explicit Backend(QObject *parent=nullptr);
    ~Backend() override;
    QVariantMap state() const { return m_state; }
    QVariantList servers() const { return m_servers; }
    QString error() const { return m_error; }
    QString voiceState() const { return m_voiceState; }
    QString speechStatus() const { return m_speechStatus; }
    bool busy() const { return m_busy; }
    Q_INVOKABLE void send(const QVariantMap &message);
    Q_INVOKABLE void capture(bool region);
    Q_INVOKABLE void windowContext();
    Q_INVOKABLE void speak(const QString &text);
    Q_INVOKABLE void mute();
    Q_INVOKABLE void dismissError();
    Q_INVOKABLE void quit() { emit quitRequested(); }
    void shutdown();
signals:
    void stateChanged();
    void serversChanged();
    void errorChanged();
    void voiceChanged();
    void speechChanged();
    void busyChanged();
    void workerEvent(const QVariantMap &value);
    void showRequested();
    void hideRequested();
    void quitRequested();
private:
    void consume();
    void fail(const QString &message);
    QProcess m_worker;
    QByteArray m_buffer;
    QVariantMap m_state;
    QVariantList m_servers;
    QString m_error, m_voiceState="idle", m_speechStatus;
    bool m_busy=false, m_stopping=false;
    QTextToSpeech *m_speech=nullptr;
};
