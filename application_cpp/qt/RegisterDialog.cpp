#include "RegisterDialog.h"

#include <QApplication>
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

RegisterDialog::RegisterDialog(const QString &lang, int themeIndex, QWidget *parent)
    : QDialog(parent), m_lang((lang == "EN") ? "EN" : "CN"), m_themeIndex(themeIndex)
{
  setModal(true);
  setWindowTitle(trText("reg_title"));
  setWindowIcon(QApplication::windowIcon());
  setFixedSize(600, 500);

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
  connect(m_langBtn, &QPushButton::clicked, this, &RegisterDialog::onToggleLanguage);
  top->addWidget(m_langBtn);

  m_themeLabel = new QLabel(this);
  top->addWidget(m_themeLabel);

  m_themeCombo = new QComboBox(this);
  m_themeCombo->setSizeAdjustPolicy(QComboBox::AdjustToContents);
  m_themeCombo->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
  connect(m_themeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this,
          &RegisterDialog::onThemeChanged);
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

  m_confirmLabel = new QLabel(this);
  m_confirmEdit = new QLineEdit(this);
  m_confirmEdit->setEchoMode(QLineEdit::Password);
  grid->addWidget(m_confirmLabel, 2, 0);
  grid->addWidget(m_confirmEdit, 2, 1);

  grid->setColumnStretch(1, 1);
  main->addLayout(grid);

  m_registerBtn = new QPushButton(this);
  m_registerBtn->setCursor(Qt::PointingHandCursor);
  m_registerBtn->setProperty("primary", true);
  connect(m_registerBtn, &QPushButton::clicked, this, &RegisterDialog::onRegister);
  main->addWidget(m_registerBtn);

  m_backLink = new QLabel(this);
  m_backLink->setTextFormat(Qt::RichText);
  m_backLink->setTextInteractionFlags(Qt::TextBrowserInteraction);
  m_backLink->setOpenExternalLinks(false);
  m_backLink->setCursor(Qt::PointingHandCursor);
  connect(m_backLink, &QLabel::linkActivated, this, [this]()
          { reject(); });
  main->addWidget(m_backLink, 0, Qt::AlignHCenter);

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

QString RegisterDialog::language() const { return m_lang; }

int RegisterDialog::themeIndex() const { return m_themeIndex; }

void RegisterDialog::onToggleLanguage()
{
  m_lang = (m_lang == "CN") ? "EN" : "CN";
  AppConfig::setLanguage(m_lang);
  applyLanguage();
}

void RegisterDialog::onThemeChanged(int idx)
{
  m_themeIndex = idx;
  AppConfig::setThemeIndex(m_themeIndex);
  applyTheme();
}

void RegisterDialog::onRegister()
{
  const QString u = m_userEdit->text().trimmed();
  const QString p = m_passEdit->text();
  const QString c = m_confirmEdit->text();
  if (u.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "请输入用户名", "Please enter username"));
    return;
  }
  if (p.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "请输入密码", "Please enter password"));
    return;
  }
  if (p != c)
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "两次输入的密码不一致", "Passwords do not match"));
    return;
  }

  if (!AppConfig::createUser(u, p))
  {
    AppConfig::showToast(
        this, pick(m_lang, "失败", "Failed"),
        pick(m_lang, "注册失败：用户名已存在或无效",
             "Registration failed: username exists or invalid"));
    return;
  }

  AppConfig::showToast(this, pick(m_lang, "成功", "Success"),
                       pick(m_lang, "注册成功", "Registered"));
  accept();
}

void RegisterDialog::applyTheme()
{
  setAutoFillBackground(false);
  AppConfig::applyEffectsGlobalTheme();

  const QString link = AppConfig::effectsAccent().name(QColor::HexRgb);
  m_backLink->setStyleSheet(QString("QLabel{background:transparent;border:0px;color:%1;}").arg(link));

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

  if (m_langBtn)
  {
    m_langBtn->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
    m_langBtn->setFlat(false);
  }
  if (m_langLabel)
    m_langLabel->setStyleSheet(labelStyle);
  if (m_themeLabel)
    m_themeLabel->setStyleSheet(labelStyle);
  if (m_userLabel)
    m_userLabel->setStyleSheet(labelStyle);
  if (m_passLabel)
    m_passLabel->setStyleSheet(labelStyle);
  if (m_confirmLabel)
    m_confirmLabel->setStyleSheet(labelStyle);
  if (m_themeCombo)
    m_themeCombo->setStyleSheet(comboStyle);
  if (m_userEdit)
    m_userEdit->setStyleSheet(editStyle);
  if (m_passEdit)
    m_passEdit->setStyleSheet(editStyle);
  if (m_confirmEdit)
    m_confirmEdit->setStyleSheet(editStyle);
}

void RegisterDialog::setUiFont()
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

void RegisterDialog::applyLanguage()
{
  setUiFont();
  setWindowTitle(trText("reg_title"));
  m_title->setText(trText("reg_title"));
  m_userLabel->setText(trText("label_username"));
  m_passLabel->setText(trText("label_password"));
  m_confirmLabel->setText(trText("label_confirm"));
  m_registerBtn->setText(trText("btn_register"));
  m_backLink->setText(QString("<a href=\"login\">%1</a>").arg(trText("link_login")));

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

  if (m_userEdit)
    m_userEdit->setPlaceholderText(pick(m_lang, "用户名", "Username"));
  if (m_passEdit)
    m_passEdit->setPlaceholderText(pick(m_lang, "密码", "Password"));
  if (m_confirmEdit)
    m_confirmEdit->setPlaceholderText(pick(m_lang, "确认密码", "Confirm Password"));

  if (m_langLabel)
    m_langLabel->setVisible(true);
  if (m_themeLabel)
    m_themeLabel->setVisible(true);
  if (m_userLabel)
    m_userLabel->setVisible(true);
  if (m_passLabel)
    m_passLabel->setVisible(true);
  if (m_confirmLabel)
    m_confirmLabel->setVisible(true);

  if (m_langBtn)
  {
    m_langBtn->adjustSize();
    m_langBtn->updateGeometry();
  }
  if (m_registerBtn)
  {
    m_registerBtn->adjustSize();
    m_registerBtn->updateGeometry();
  }
}

QString RegisterDialog::trText(const QString &key) const
{
  if (key == "reg_title")
    return pick(m_lang, "注册新用户", "Register New User");
  if (key == "label_username")
    return pick(m_lang, "用户名:", "Username:");
  if (key == "label_password")
    return pick(m_lang, "密  码:", "Password:");
  if (key == "label_confirm")
    return pick(m_lang, "确认密码:", "Confirm Password:");
  if (key == "btn_register")
    return pick(m_lang, "注册", "Register");
  if (key == "link_login")
    return pick(m_lang, "已有账户？返回登录", "Already have an account? Back to Login");
  if (key == "label_language")
    return pick(m_lang, "语言", "Language");
  if (key == "lang_switch")
    return pick(m_lang, "English", "中文");
  if (key == "label_theme")
    return pick(m_lang, "主题", "Theme");
  return key;
}
