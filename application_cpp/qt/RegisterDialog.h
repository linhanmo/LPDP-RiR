#pragma once

#include <QColor>
#include <QString>
#include <QDialog>

class QLabel;
class QLineEdit;
class QComboBox;
class QPushButton;

class RegisterDialog final : public QDialog
{
  Q_OBJECT

public:
  explicit RegisterDialog(const QString &lang, int themeIndex, QWidget *parent = nullptr);

  QString language() const;
  int themeIndex() const;

private slots:
  void onToggleLanguage();
  void onThemeChanged(int idx);
  void onRegister();

private:
  void applyTheme();
  void applyLanguage();
  void setUiFont();
  QString trText(const QString &key) const;

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
  QLabel *m_confirmLabel = nullptr;
  QLineEdit *m_userEdit = nullptr;
  QLineEdit *m_passEdit = nullptr;
  QLineEdit *m_confirmEdit = nullptr;
  QPushButton *m_registerBtn = nullptr;
  QLabel *m_backLink = nullptr;
};
