#include <QGuiApplication>
#include <QJsonDocument>
#include <QJsonArray>
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

static QQuickItem *visualItem(QQuickItem *root,const QString &name){
    if(root->objectName()==name)return root;
    for(auto *child:root->childItems())if(auto *found=visualItem(child,name))return found;
    return nullptr;
}

class UITest:public QObject {
    Q_OBJECT
private slots:
    void historicalContextSelectionAndPreview(){
        QTemporaryDir dir;QVERIFY(dir.isValid());
        qputenv("CLICKY_CONFIG_HOME",(dir.path()+"/config").toUtf8());qputenv("CLICKY_DATA_HOME",(dir.path()+"/data").toUtf8());qputenv("CLICKY_DISABLE_TTS","1");
        QProcess seed;seed.setWorkingDirectory(QStringLiteral(CLICKY_PROJECT));
        seed.start(QStringLiteral(CLICKY_PROJECT)+"/.venv/bin/python",{"-c",
            "import json; from clicky.storage import Store; from clicky.config import Config; s=Store(); a=s.new('Test archive'); m=s.add(a,'user','INTENDED_UI_CONTEXT'); s.add(a,'assistant','UNSELECTED_UI_CONTEXT'); b=s.new('Current'); c=Config(); c.data['last_conversation']=b; c.save(); print(json.dumps([a,m,b])); s.close()"});
        QVERIFY(seed.waitForFinished(5000));QCOMPARE(seed.exitCode(),0);const auto data=QJsonDocument::fromJson(seed.readAllStandardOutput()).array();QCOMPARE(data.size(),3);
        Backend backend;Theme theme;Translator translator;QQmlApplicationEngine engine;
        engine.rootContext()->setContextProperty("backend",&backend);engine.rootContext()->setContextProperty("theme",&theme);engine.rootContext()->setContextProperty("translator",&translator);
        engine.load(QUrl("qrc:/Main.qml"));QVERIFY(!engine.rootObjects().isEmpty());auto *window=qobject_cast<QQuickWindow*>(engine.rootObjects().first());window->show();
        QTRY_COMPARE_WITH_TIMEOUT(backend.state().value("conversation").toString(),data[2].toString(),10000);
        const auto addName="addContext_"+data[0].toString();QTRY_VERIFY(visualItem(window->contentItem(),addName));
        auto click=[&](QQuickItem *item){QTest::mouseClick(window,Qt::LeftButton,Qt::NoModifier,item->mapToScene(QPointF(item->width()/2,item->height()/2)).toPoint());};
        click(visualItem(window->contentItem(),addName));auto *dialog=window->findChild<QObject*>("contextDialog");QVERIFY(dialog);QTRY_VERIFY(dialog->property("opened").toBool());
        QCOMPARE(backend.state().value("conversation").toString(),data[2].toString());
        const auto selectName="contextSelect_"+QString::number(data[1].toInt());QTRY_VERIFY(visualItem(window->contentItem(),selectName));click(visualItem(window->contentItem(),selectName));
        QTRY_COMPARE_WITH_TIMEOUT(backend.state().value("selections").toList().size(),1,5000);QMetaObject::invokeMethod(dialog,"close");QTRY_VERIFY(!dialog->property("visible").toBool());
        auto *input=window->findChild<QQuickItem*>("messageInput");QVERIFY(input);input->setProperty("text","question");QMetaObject::invokeMethod(window,"inspectRequest");
        auto *preview=window->findChild<QObject*>("requestDialog");QTRY_VERIFY(preview->property("opened").toBool());
        const auto request=QJsonDocument::fromVariant(window->property("requestPreview")).toJson();QVERIFY(request.contains("INTENDED_UI_CONTEXT"));QVERIFY(!request.contains("UNSELECTED_UI_CONTEXT"));QMetaObject::invokeMethod(preview,"close");QTRY_VERIFY(!preview->property("visible").toBool());
        const auto removeName="removeContext_"+QString::number(data[1].toInt());QTRY_VERIFY(visualItem(window->contentItem(),removeName));click(visualItem(window->contentItem(),removeName));
        QTRY_COMPARE_WITH_TIMEOUT(backend.state().value("selections").toList().size(),0,5000);backend.shutdown();
    }
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
            QTRY_VERIFY_WITH_TIMEOUT(backend.servers().first().toMap().value("state").toString()=="connected",10000);
            QSignalSpy spy(&backend,&Backend::workerEvent);
            backend.send({{"cmd","tool_call"},{"server","workspace"},{"tool","capabilities"},{"arguments",QVariantMap{}}});
            auto *approval=window->findChild<QObject*>("approvalDialog");QVERIFY(approval);QTRY_VERIFY_WITH_TIMEOUT(approval->property("opened").toBool(),5000);
            QString approvalId;
            for(const auto &row:spy){auto v=row.first().toMap();if(v.value("event")=="approval")approvalId=v.value("id").toString();}
            QVERIFY(!approvalId.isEmpty());backend.send({{"cmd","approve"},{"id",approvalId},{"allow",true}});
            QTRY_VERIFY_WITH_TIMEOUT(!backend.busy(),5000);
            QTRY_VERIFY_WITH_TIMEOUT(!backend.state().value("activity").toList().isEmpty(),5000);
            QCOMPARE(backend.state().value("activity").toList().first().toMap().value("status").toString(),QString("completed"));
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
