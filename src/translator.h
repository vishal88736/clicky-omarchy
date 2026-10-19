#pragma once
#include <QTranslator>
#include <QVariantMap>
#include <QTimer>
class Translator:public QTranslator{
    Q_OBJECT
    Q_PROPERTY(QString language READ language NOTIFY changed)
public:
    explicit Translator(QObject *parent=nullptr);
    QString language()const{return m_language;}
    QString translate(const char*,const char*,const char* =nullptr,int =-1)const override;
    bool isEmpty()const override{return m_strings.isEmpty();}
signals:void changed();
private:
    void reload();
    QString m_language;
    QVariantMap m_strings;
    QTimer m_poll;
};
