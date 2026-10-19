#include <QGuiApplication>
#include <QJsonDocument>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickStyle>
#include <QQuickWindow>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QTest>
#include <QFile>
#include "../src/backend.h"
#include "../src/theme.h"
#include "../src/translator.h"

class UITest:public QObject {
    Q_OBJECT
private slots:
    void realUiDraftRestartAndDialogs(){
        QTemporaryDir dir;QVERIFY(dir.isValid());
        qputenv("CLICKY_CONFIG_HOME",(dir.path()+"/config").toUtf8());qputenv("CLICKY_DATA_HOME",(dir.path()+"/data").toUtf8());
        qputenv("CLICKY_DISABLE_TTS","1");qputenv("CLICKY_THEME_DIR",(dir.path()+"/theme").toUtf8());
        QString cid;
        {
            Backend backend;Theme theme;Translator translator;QQmlApplicationEngine engine;
            engine.rootContext()->setContextProperty("backend",&backend);engine.rootContext()->setContextProperty("theme",&theme);engine.rootContext()->setContextProperty("translator",&translator);
            engine.load(QUrl("qrc:/Main.qml"));QVERIFY(!engine.rootObjects().isEmpty());
            auto *window=qobject_cast<QQuickWindow*>(engine.rootObjects().first());QVERIFY(window);window->show();
            QTRY_VERIFY_WITH_TIMEOUT(!backend.state().value("conversation").toString().isEmpty(),10000);
            QTRY_COMPARE_WITH_TIMEOUT(backend.servers().size(),2,10000);
            auto *input=window->findChild<QQuickItem*>("messageInput");QVERIFY(input);input->forceActiveFocus();
            for(char ch:QByteArray("an unfinished draft"))QTest::keyClick(window,ch);
            QTest::qWait(300);backend.send({{"cmd","state"}});
            QTRY_COMPARE_WITH_TIMEOUT(backend.state().value("draft").toString(),QString("an unfinished draft"),5000);
            cid=backend.state().value("conversation").toString();
            QMetaObject::invokeMethod(window,"newConversation");
            QTRY_VERIFY_WITH_TIMEOUT(backend.state().value("conversation").toString()!=cid,5000);
            backend.send({{"cmd","switch"},{"id",cid}});
            QTRY_COMPARE_WITH_TIMEOUT(input->property("text").toString(),QString("an unfinished draft"),5000);
            for(const auto &name:{"settingsDialog","toolsDialog"}){
                auto *dialog=window->findChild<QObject*>(name);QVERIFY(dialog);QVERIFY(QMetaObject::invokeMethod(dialog,"open"));
                QTRY_VERIFY(dialog->property("opened").toBool());QVERIFY(QMetaObject::invokeMethod(dialog,"close"));
            }
            input->forceActiveFocus();QTest::keyClick(window,Qt::Key_Return,Qt::ControlModifier);
            auto *preview=window->findChild<QObject*>("requestDialog");QVERIFY(preview);QTRY_VERIFY_WITH_TIMEOUT(preview->property("opened").toBool(),5000);
            QMetaObject::invokeMethod(preview,"close");
            const auto image=window->grabWindow();QVERIFY(!image.isNull());
            QVERIFY(image.save(dir.path()+"/ui.png"));backend.shutdown();
        }
        Backend restored;
        QTRY_VERIFY_WITH_TIMEOUT(!restored.state().value("conversation").toString().isEmpty(),10000);
        QCOMPARE(restored.state().value("conversation").toString(),cid);
        QCOMPARE(restored.state().value("draft").toString(),QString("an unfinished draft"));restored.shutdown();
    }
};
int main(int argc,char**argv){qputenv("QT_QPA_PLATFORM","offscreen");qputenv("QT_QUICK_BACKEND","software");qputenv("QT_FORCE_STDERR_LOGGING","1");QGuiApplication app(argc,argv);QQuickStyle::setStyle("Material");UITest test;return QTest::qExec(&test,argc,argv);}
#include "qt_tests.moc"
