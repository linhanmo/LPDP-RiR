#pragma once

#include <QMainWindow>
#include <QMap>
#include <QString>

class QStackedWidget;
class NavigationBar;
class HomePage;
class IntroductionPage;
class ModelInterfacePage;
class HistoryPage;
class Analyze3DWindow;

class MainWindow final : public QMainWindow
{
  Q_OBJECT

public:
  explicit MainWindow(QWidget *parent = nullptr);

  QString language() const;
  QString username() const;
  void setUsername(const QString &username);

signals:
  void logoutRequested();
  void changePasswordRequested();

public slots:
  void setLanguage(const QString &lang);
  void setThemeIndex(int index);

private slots:
  void onNavigate(const QString &pageKey);
  void onToggleLanguage();

private:
  void applyTheme();
  void updateLanguage();

  QString m_language = "CN";
  int m_themeIndex = 1;
  QString m_username;

  QWidget *m_root = nullptr;
  NavigationBar *m_navbar = nullptr;
  QStackedWidget *m_stack = nullptr;

  HomePage *m_home = nullptr;
  IntroductionPage *m_intro = nullptr;
  ModelInterfacePage *m_model = nullptr;
  HistoryPage *m_history = nullptr;

  Analyze3DWindow *m_analyze3d = nullptr;
};
