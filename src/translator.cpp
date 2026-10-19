#include "translator.h"
#include <QDir>
#include <QFile>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocale>
#include <QRegularExpression>
Translator::Translator(QObject *parent):QTranslator(parent){connect(&m_poll,&QTimer::timeout,this,[this]{reload();});m_poll.start(1500);reload();}
QString Translator::translate(const char*,const char* source,const char*,int)const{return m_strings.value(QString::fromUtf8(source)).toString();}
void Translator::reload(){
    QFile file(qEnvironmentVariable("CLICKY_LANGUAGE_FILE",QDir::homePath()+"/.config/omarchy/language"));QString lang="en";
    if(file.open(QIODevice::ReadOnly))lang=QString::fromUtf8(file.readLine()).trimmed();
    if(!QRegularExpression("^[a-z]{2,3}(-[A-Za-z]{2})?$").match(lang).hasMatch())lang="en";
    if(lang==m_language)return;
    m_language=lang;m_strings.clear();
    QStringList codes{"en",lang.section('-',0,0),lang};codes.removeDuplicates();
    for(const auto &code:codes){QFile catalog(":/i18n/"+code+".json");if(catalog.open(QIODevice::ReadOnly)){
        const auto values=QJsonDocument::fromJson(catalog.readAll()).object().toVariantMap();
        for(auto it=values.cbegin();it!=values.cend();++it)m_strings[it.key()]=it.value();}}
    QLocale locale(lang);QFile registry("/usr/share/omarchy/default/i18n/locales.json");
    if(registry.open(QIODevice::ReadOnly)){
        const auto name=QJsonDocument::fromJson(registry.readAll()).object().value(lang).toObject().value("formatLocale").toString();
        if(!name.isEmpty())locale=QLocale(name);
    }
    QLocale::setDefault(locale);QGuiApplication::setLayoutDirection(locale.textDirection());emit changed();
}
