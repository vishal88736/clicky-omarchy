QT += core gui qml quick quickcontrols2 network texttospeech
CONFIG += c++17 release
TARGET = clicky
TEMPLATE = app
SOURCES += src/main.cpp src/backend.cpp src/theme.cpp src/translator.cpp
HEADERS += src/backend.h src/theme.h src/translator.h
RESOURCES += src/resources.qrc
DEFINES += CLICKY_PROJECT=\"\\\"$$PWD\\\"\"
