QT += core gui qml quick quickcontrols2 network texttospeech testlib
CONFIG += c++17 console testcase
TARGET = clicky_qt_tests
SOURCES += qt_tests.cpp ../src/backend.cpp ../src/theme.cpp ../src/translator.cpp
HEADERS += ../src/backend.h ../src/theme.h ../src/translator.h
RESOURCES += ../src/resources.qrc
DEFINES += CLICKY_PROJECT=\"\\\"$$PWD/..\\\"\"
