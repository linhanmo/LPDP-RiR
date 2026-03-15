#include "LoginWindow.h"

#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QFont>
#include <QFrame>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPair>
#include <QPushButton>
#include <QVector>
#include <QVBoxLayout>

#include "AppConfig.h"

namespace
{
  QString pick(const QString &lang, const QString &cn, const QString &en)
  {
    return (lang == "EN") ? en : cn;
  }

  QVector<QPair<QString, QString>> themePairs()
  {
    return {
        {"深空玻璃", "Deep Space Glass"},
        {"星云紫光", "Nebula Violet"},
        {"极光薄荷", "Aurora Mint"},
        {"霓虹玫红", "Neon Pink"},
        {"青紫渐变", "Cyan Violet"},
        {"深夜模式", "Night Mode"},
    };
  }
}

LoginWindow::LoginWindow(QWidget *parent) : QDialog(parent)
{
  setModal(true);
  setWindowTitle(trText("login_title"));
  setWindowIcon(QApplication::windowIcon());
  setFixedSize(600, 460);

  m_lang = AppConfig::language();
  m_themeIndex = AppConfig::themeIndex();

  const auto creds = AppConfig::credentials();

  auto *outer = new QVBoxLayout();
  outer->setContentsMargins(18, 18, 18, 18);
  outer->setSpacing(0);
  setLayout(outer);

  auto *panel = new QFrame(this);
  panel->setStyleSheet(
      "QFrame{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:22px;}");
  AppConfig::installGlassCard(panel);
  outer->addWidget(panel, 1);

  auto *root = new QVBoxLayout();
  root->setContentsMargins(30, 20, 30, 20);
  root->setSpacing(0);
  panel->setLayout(root);

  auto *top = new QHBoxLayout();
  top->setContentsMargins(0, 0, 0, 0);
  top->setSpacing(6);
  top->addStretch(1);

  m_langLabel = new QLabel(this);
  top->addWidget(m_langLabel);

  m_langBtn = new QPushButton(this);
  m_langBtn->setFlat(true);
  m_langBtn->setCursor(Qt::PointingHandCursor);
  connect(m_langBtn, &QPushButton::clicked, this, &LoginWindow::onToggleLanguage);
  top->addWidget(m_langBtn);

  m_themeLabel = new QLabel(this);
  top->addWidget(m_themeLabel);

  m_themeCombo = new QComboBox(this);
  m_themeCombo->setSizeAdjustPolicy(QComboBox::AdjustToContents);
  m_themeCombo->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
  connect(m_themeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this,
          &LoginWindow::onThemeChanged);
  top->addWidget(m_themeCombo);

  root->addLayout(top);

  auto *main = new QVBoxLayout();
  main->setContentsMargins(0, 30, 0, 0);
  main->setSpacing(12);
  root->addLayout(main, 1);

  m_title = new QLabel(this);
  m_title->setAlignment(Qt::AlignCenter);
  m_title->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:18px;font-weight:800;}");
  main->addWidget(m_title);
  main->addSpacing(8);

  auto *grid = new QGridLayout();
  grid->setContentsMargins(0, 0, 0, 0);
  grid->setHorizontalSpacing(12);
  grid->setVerticalSpacing(10);

  m_userLabel = new QLabel(this);
  m_userEdit = new QLineEdit(this);
  grid->addWidget(m_userLabel, 0, 0);
  grid->addWidget(m_userEdit, 0, 1);

  m_passLabel = new QLabel(this);
  m_passEdit = new QLineEdit(this);
  m_passEdit->setEchoMode(QLineEdit::Password);
  grid->addWidget(m_passLabel, 1, 0);
  grid->addWidget(m_passEdit, 1, 1);

  grid->setColumnStretch(1, 1);
  main->addLayout(grid);

  m_remember = new QCheckBox(this);
  m_remember->setChecked(creds.rememberMe);
  main->addWidget(m_remember, 0, Qt::AlignLeft);

  m_loginBtn = new QPushButton(this);
  m_loginBtn->setCursor(Qt::PointingHandCursor);
  m_loginBtn->setProperty("primary", true);
  connect(m_loginBtn, &QPushButton::clicked, this, &LoginWindow::onLogin);
  connect(m_passEdit, &QLineEdit::returnPressed, this, &LoginWindow::onLogin);
  main->addWidget(m_loginBtn);

  auto *links = new QHBoxLayout();
  links->setContentsMargins(0, 0, 0, 0);
  links->setSpacing(0);

  m_registerLink = new QLabel(this);
  m_registerLink->setTextFormat(Qt::RichText);
  m_registerLink->setTextInteractionFlags(Qt::TextBrowserInteraction);
  m_registerLink->setOpenExternalLinks(false);
  m_registerLink->setCursor(Qt::PointingHandCursor);
  connect(m_registerLink, &QLabel::linkActivated, this, &LoginWindow::onRegisterLink);
  links->addWidget(m_registerLink, 0, Qt::AlignLeft);

  links->addStretch(1);

  m_changePassLink = new QLabel(this);
  m_changePassLink->setTextFormat(Qt::RichText);
  m_changePassLink->setTextInteractionFlags(Qt::TextBrowserInteraction);
  m_changePassLink->setOpenExternalLinks(false);
  m_changePassLink->setCursor(Qt::PointingHandCursor);
  connect(m_changePassLink, &QLabel::linkActivated, this, &LoginWindow::onChangePasswordLink);
  links->addWidget(m_changePassLink, 0, Qt::AlignRight);

  main->addLayout(links);

  if (!creds.username.isEmpty())
  {
    m_userEdit->setText(creds.username);
    m_passEdit->setText(creds.password);
  }

  const auto names = themePairs();
  for (const auto &n : names)
  {
    m_themeCombo->addItem(pick(m_lang, n.first, n.second));
  }
  if (m_themeIndex >= 0 && m_themeIndex < m_themeCombo->count())
  {
    m_themeCombo->setCurrentIndex(m_themeIndex);
  }
  else
  {
    m_themeCombo->setCurrentIndex(1);
    m_themeIndex = 1;
  }

  applyTheme();
  applyLanguage();
}

QString LoginWindow::language() const { return m_lang; }

int LoginWindow::themeIndex() const { return m_themeIndex; }

QString LoginWindow::username() const { return m_userEdit ? m_userEdit->text() : QString(); }

void LoginWindow::onToggleLanguage()
{
  m_lang = (m_lang == "CN") ? "EN" : "CN";
  AppConfig::setLanguage(m_lang);
  applyLanguage();
}

void LoginWindow::onThemeChanged(int idx)
{
  m_themeIndex = idx;
  AppConfig::setThemeIndex(m_themeIndex);
  applyTheme();
}

void LoginWindow::onLogin()
{
  const QString u = m_userEdit->text().trimmed();
  const QString p = m_passEdit->text();
  if (u.isEmpty() || p.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "登录失败", "Login Failed"),
                         pick(m_lang, "请输入用户名和密码", "Please enter username and password"));
    return;
  }

  if (!AppConfig::authenticateUser(u, p))
  {
    AppConfig::showToast(this, pick(m_lang, "登录失败", "Login Failed"),
                         pick(m_lang, "用户名或密码错误", "Incorrect username or password"));
    return;
  }

  AppConfig::saveCredentials(u, p, m_remember->isChecked());
  accept();
}

void LoginWindow::onRegisterLink() { emit registerRequested(m_lang, m_themeIndex); }

void LoginWindow::onChangePasswordLink()
{
  emit changePasswordRequested(m_userEdit->text().trimmed(), m_lang, m_themeIndex);
}

void LoginWindow::applyTheme()
{
  setAutoFillBackground(false);
  AppConfig::applyEffectsGlobalTheme();

  const QString link = AppConfig::effectsAccent().name(QColor::HexRgb);
  m_registerLink->setStyleSheet(QString("QLabel{background:transparent;border:0px;color:%1;}").arg(link));
  m_changePassLink->setStyleSheet(QString("QLabel{background:transparent;border:0px;color:%1;}").arg(link));

  const QColor a = AppConfig::effectsAccent();
  const QString focusBorder = QString("rgba(%1,%2,%3,0.45)").arg(a.red()).arg(a.green()).arg(a.blue());
  const QString labelStyle =
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.72);font-size:12px;font-weight:800;}";
  const QString editStyle = QString(
                                "QLineEdit{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);"
                                "border-radius:12px;padding:8px 12px;color:rgba(255,255,255,0.92);}"
                                "QLineEdit:focus{border:1px solid %1;}")
                                .arg(focusBorder);
  const QString comboStyle =
      "QComboBox{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:12px;padding:8px 12px;color:rgba(255,255,255,0.92);}"
      "QComboBox:hover{background:rgba(255,255,255,0.08);}"
      "QComboBox QAbstractItemView{background:#0C1426;color:rgba(255,255,255,0.92);border:1px solid rgba(255,255,255,0.12);selection-background-color:rgba(103,209,255,0.14);outline:0px;}";

  if (m_langLabel)
    m_langLabel->setStyleSheet(labelStyle);
  if (m_themeLabel)
    m_themeLabel->setStyleSheet(labelStyle);
  if (m_userLabel)
    m_userLabel->setStyleSheet(labelStyle);
  if (m_passLabel)
    m_passLabel->setStyleSheet(labelStyle);

  if (m_langBtn)
  {
    m_langBtn->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
    m_langBtn->setFlat(false);
  }
  if (m_themeCombo)
    m_themeCombo->setStyleSheet(comboStyle);
  if (m_userEdit)
    m_userEdit->setStyleSheet(editStyle);
  if (m_passEdit)
    m_passEdit->setStyleSheet(editStyle);
}

void LoginWindow::setUiFont()
{
  QFont f;
  if (m_lang == "EN")
  {
    f.setFamily("Arial");
    f.setPointSize(10);
  }
  else
  {
    f.setFamily("Microsoft YaHei");
    f.setPointSize(10);
  }
  setFont(f);
}

void LoginWindow::applyLanguage()
{
  setUiFont();
  setWindowTitle(trText("login_title"));
  m_title->setText(trText("login_welcome"));
  m_userLabel->setText(trText("label_username"));
  m_passLabel->setText(trText("label_password"));
  m_remember->setText(trText("remember_me"));
  m_loginBtn->setText(trText("btn_login"));

  m_langLabel->setText(trText("label_language"));
  m_langBtn->setText(trText("lang_switch"));
  m_themeLabel->setText(trText("label_theme"));

  const auto names = themePairs();
  const int old = m_themeCombo->currentIndex();
  m_themeCombo->blockSignals(true);
  m_themeCombo->clear();
  for (const auto &n : names)
  {
    m_themeCombo->addItem(pick(m_lang, n.first, n.second));
  }
  m_themeCombo->setCurrentIndex(old >= 0 ? old : m_themeIndex);
  m_themeCombo->blockSignals(false);
  m_themeCombo->setMinimumWidth(0);
  m_themeCombo->setMinimumWidth(m_themeCombo->sizeHint().width());
  m_themeCombo->updateGeometry();

  m_registerLink->setText(QString("<a href=\"register\">%1</a>").arg(trText("link_register")));
  m_changePassLink->setText(
      QString("<a href=\"cp\">%1</a>").arg(trText("link_change_password")));

  if (m_userEdit)
    m_userEdit->setPlaceholderText(pick(m_lang, "用户名", "Username"));
  if (m_passEdit)
    m_passEdit->setPlaceholderText(pick(m_lang, "密码", "Password"));

  if (m_langLabel)
    m_langLabel->setVisible(true);
  if (m_themeLabel)
    m_themeLabel->setVisible(true);
  if (m_userLabel)
    m_userLabel->setVisible(true);
  if (m_passLabel)
    m_passLabel->setVisible(true);

  if (m_langBtn)
  {
    m_langBtn->adjustSize();
    m_langBtn->updateGeometry();
  }
  if (m_loginBtn)
  {
    m_loginBtn->adjustSize();
    m_loginBtn->updateGeometry();
  }
}

QString LoginWindow::trText(const QString &key) const
{
  if (key == "login_title")
    return pick(m_lang, "登录系统", "Login System");
  if (key == "login_welcome")
    return pick(m_lang, "欢迎登录", "Welcome Login");
  if (key == "label_username")
    return pick(m_lang, "用户名:", "Username:");
  if (key == "label_password")
    return pick(m_lang, "密  码:", "Password:");
  if (key == "btn_login")
    return pick(m_lang, "登录", "Login");
  if (key == "link_register")
    return pick(m_lang, "注册新用户", "Register New User");
  if (key == "link_change_password")
    return pick(m_lang, "修改密码", "Change Password");
  if (key == "remember_me")
    return pick(m_lang, "记住我", "Remember Me");
  if (key == "label_language")
    return pick(m_lang, "语言", "Language");
  if (key == "lang_switch")
    return pick(m_lang, "English", "中文");
  if (key == "label_theme")
    return pick(m_lang, "主题", "Theme");
  return key;
}
