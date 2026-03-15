#pragma once

#include <QColor>
#include <QString>
#include <QDialog>

class QLabel;
class QLineEdit;
class QCheckBox;
class QComboBox;
class QPushButton;

class LoginWindow final : public QDialog
{
  Q_OBJECT

public:
  explicit LoginWindow(QWidget *parent = nullptr);

  QString language() const;
  int themeIndex() const;
  QString username() const;

signals:
  void registerRequested(const QString &lang, int themeIndex);
  void changePasswordRequested(const QString &defaultUsername, const QString &lang,
                               int themeIndex);

private slots:
  void onToggleLanguage();
  void onThemeChanged(int idx);
  void onLogin();
  void onRegisterLink();
  void onChangePasswordLink();

private:
  void applyTheme();
  void applyLanguage();
  QString trText(const QString &key) const;
  void setUiFont();

  QString m_lang = "CN";
  int m_themeIndex = 1;
  QColor m_bg = QColor("#0B1220");

  QLabel *m_langLabel = nullptr;
  QPushButton *m_langBtn = nullptr;
  QLabel *m_themeLabel = nullptr;
  QComboBox *m_themeCombo = nullptr;

  QLabel *m_title = nullptr;
  QLabel *m_userLabel = nullptr;
  QLabel *m_passLabel = nullptr;
  QLineEdit *m_userEdit = nullptr;
  QLineEdit *m_passEdit = nullptr;
  QCheckBox *m_remember = nullptr;
  QPushButton *m_loginBtn = nullptr;
  QLabel *m_registerLink = nullptr;
  QLabel *m_changePassLink = nullptr;
};
