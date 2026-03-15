#pragma once

#include <QColor>
#include <QMap>
#include <QString>
#include <QWidget>

class QComboBox;
class QLabel;
class QToolButton;
class NavButton;

class NavigationBar final : public QWidget
{
  Q_OBJECT

public:
  struct TextPair
  {
    QString cn;
    QString en;
  };

  explicit NavigationBar(QWidget *parent = nullptr);

  void setLanguage(const QString &lang);
  void setThemeColor(const QColor &bg);
  void setActivePage(const QString &pageKey);
  void setUsername(const QString &username);

signals:
  void navigateTo(const QString &pageKey);
  void toggleLanguageRequested();
  void themeIndexChanged(int index);
  void logoutRequested();
  void changePasswordRequested();

private:
  QString t(const TextPair &p) const;
  void rebuildThemeNames();
  void applyButtonStyles();

  QString m_lang = "CN";
  QColor m_bg = QColor("#0B1220");
  QString m_activePage = "Homepage";

  QMap<QString, NavButton *> m_buttons;
  QMap<QString, QWidget *> m_wrappers;

  QLabel *m_langLabel = nullptr;
  NavButton *m_langBtn = nullptr;
  QLabel *m_themeLabel = nullptr;
  QComboBox *m_themeCombo = nullptr;
  QToolButton *m_userButton = nullptr;
};
