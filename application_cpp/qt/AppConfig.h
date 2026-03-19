#pragma once

#include <QColor>
#include <QProcessEnvironment>
#include <QString>
#include <QVector>
#include <functional>

class QWidget;
class QProcess;

struct AppCredentials
{
  bool rememberMe = false;
  QString username;
  QString password;
};

class AppConfig final
{
public:
  static QString configFilePath();
  static QString databaseFilePath();
  static QString sessionFilePath();
  static QString pythonExecutablePath();

  static QString language();
  static void setLanguage(const QString &lang);

  static int performanceThreads();
  static int performanceInteropThreads();
  static int performanceWorkers();
  static QString performancePriority();
  static QProcessEnvironment pythonProcessEnvironment();
  static void configurePythonProcess(QProcess *proc);

  static int themeIndex();
  static void setThemeIndex(int index);
  static QColor themeColor(int index);
  static QVector<QColor> themeColorList();

  static AppCredentials credentials();
  static void saveCredentials(const QString &username, const QString &password, bool rememberMe);

  static bool createUser(const QString &username, const QString &password);
  static bool authenticateUser(const QString &username, const QString &password);
  static bool changePassword(const QString &username, const QString &oldPassword,
                             const QString &newPassword);

  static QString currentUser();
  static void setCurrentUser(const QString &username);

  static QVector<QString> userHistoryFolders(const QString &username);

  static int cleanupInvalidRecords();

  static QColor effectsBg();
  static QColor effectsCard();
  static QColor effectsCard2();
  static QColor effectsBorder();
  static QColor effectsText();
  static QColor effectsMuted();
  static QColor effectsAccent();
  static QColor effectsAccent2();

  static QString effectsGlobalStyleSheet();
  static void applyEffectsGlobalTheme();

  static void installGlassCard(QWidget *card);

  static void showToast(QWidget *anchor, const QString &title, const QString &desc,
                        int durationMs = 2400);

  static void showToastAction(QWidget *anchor, const QString &title, const QString &desc,
                              const QString &actionText,
                              const std::function<void()> &onAction = std::function<void()>(),
                              int durationMs = 5000);
};
