#include "ChangePasswordDialog.h"

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

ChangePasswordDialog::ChangePasswordDialog(const QString &defaultUsername, const QString &lang,
                                           int themeIndex, QWidget *parent)
    : QDialog(parent),
      m_defaultUsername(defaultUsername),
      m_lang((lang == "EN") ? "EN" : "CN"),
      m_themeIndex(themeIndex)
{
  setModal(true);
  setWindowTitle(trText("cp_title"));
  setWindowIcon(QApplication::windowIcon());
  setFixedSize(640, 560);

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
  connect(m_langBtn, &QPushButton::clicked, this, &ChangePasswordDialog::onToggleLanguage);
  top->addWidget(m_langBtn);

  m_themeLabel = new QLabel(this);
  top->addWidget(m_themeLabel);

  m_themeCombo = new QComboBox(this);
  m_themeCombo->setSizeAdjustPolicy(QComboBox::AdjustToContents);
  m_themeCombo->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
  connect(m_themeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this,
          &ChangePasswordDialog::onThemeChanged);
  top->addWidget(m_themeCombo);

  root->addLayout(top);

  auto *main = new QVBoxLayout();
  main->setContentsMargins(0, 30, 0, 0);
  main->setSpacing(16);
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
  grid->setVerticalSpacing(14);

  m_userLabel = new QLabel(this);
  m_userEdit = new QLineEdit(this);
  m_userEdit->setText(m_defaultUsername);
  if (!m_defaultUsername.isEmpty())
    m_userEdit->setReadOnly(true);
  grid->addWidget(m_userLabel, 0, 0);
  grid->addWidget(m_userEdit, 0, 1);

  m_oldLabel = new QLabel(this);
  m_oldEdit = new QLineEdit(this);
  m_oldEdit->setEchoMode(QLineEdit::Password);
  grid->addWidget(m_oldLabel, 1, 0);
  grid->addWidget(m_oldEdit, 1, 1);

  m_newLabel = new QLabel(this);
  m_newEdit = new QLineEdit(this);
  m_newEdit->setEchoMode(QLineEdit::Password);
  grid->addWidget(m_newLabel, 2, 0);
  grid->addWidget(m_newEdit, 2, 1);

  m_confirmLabel = new QLabel(this);
  m_confirmEdit = new QLineEdit(this);
  m_confirmEdit->setEchoMode(QLineEdit::Password);
  grid->addWidget(m_confirmLabel, 3, 0);
  grid->addWidget(m_confirmEdit, 3, 1);

  grid->setColumnStretch(1, 1);
  main->addLayout(grid);

  m_changeBtn = new QPushButton(this);
  m_changeBtn->setCursor(Qt::PointingHandCursor);
  m_changeBtn->setProperty("primary", true);
  connect(m_changeBtn, &QPushButton::clicked, this, &ChangePasswordDialog::onChange);
  main->addWidget(m_changeBtn);

  m_backBtn = new QPushButton(this);
  m_backBtn->setCursor(Qt::PointingHandCursor);
  connect(m_backBtn, &QPushButton::clicked, this, [this]()
          { reject(); });
  main->addWidget(m_backBtn);

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

QString ChangePasswordDialog::language() const { return m_lang; }

int ChangePasswordDialog::themeIndex() const { return m_themeIndex; }

void ChangePasswordDialog::onToggleLanguage()
{
  m_lang = (m_lang == "CN") ? "EN" : "CN";
  AppConfig::setLanguage(m_lang);
  applyLanguage();
}

void ChangePasswordDialog::onThemeChanged(int idx)
{
  m_themeIndex = idx;
  AppConfig::setThemeIndex(m_themeIndex);
  applyTheme();
}

void ChangePasswordDialog::onChange()
{
  const QString u = m_userEdit->text().trimmed();
  const QString oldp = m_oldEdit->text();
  const QString newp = m_newEdit->text();
  const QString c = m_confirmEdit->text();

  if (u.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "请输入用户名", "Please enter username"));
    return;
  }
  if (oldp.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "请输入旧密码", "Please enter old password"));
    return;
  }
  if (newp.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "请输入新密码", "Please enter new password"));
    return;
  }
  if (newp != c)
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Warning"),
                         pick(m_lang, "两次输入的新密码不一致", "New passwords do not match"));
    return;
  }

  if (!AppConfig::changePassword(u, oldp, newp))
  {
    AppConfig::showToast(
        this, pick(m_lang, "失败", "Failed"),
        pick(m_lang, "修改失败：用户名不存在或旧密码错误",
             "Change failed: user not found or old password incorrect"));
    return;
  }

  AppConfig::showToast(this, pick(m_lang, "成功", "Success"),
                       pick(m_lang, "密码修改成功", "Password changed"));
  accept();
}

void ChangePasswordDialog::applyTheme()
{
  setAutoFillBackground(false);
  AppConfig::applyEffectsGlobalTheme();

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
  if (m_oldLabel)
    m_oldLabel->setStyleSheet(labelStyle);
  if (m_newLabel)
    m_newLabel->setStyleSheet(labelStyle);
  if (m_confirmLabel)
    m_confirmLabel->setStyleSheet(labelStyle);
  if (m_themeCombo)
    m_themeCombo->setStyleSheet(comboStyle);
  if (m_userEdit)
    m_userEdit->setStyleSheet(editStyle);
  if (m_oldEdit)
    m_oldEdit->setStyleSheet(editStyle);
  if (m_newEdit)
    m_newEdit->setStyleSheet(editStyle);
  if (m_confirmEdit)
    m_confirmEdit->setStyleSheet(editStyle);
}

void ChangePasswordDialog::setUiFont()
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

void ChangePasswordDialog::applyLanguage()
{
  setUiFont();
  setWindowTitle(trText("cp_title"));
  m_title->setText(trText("cp_title"));
  m_userLabel->setText(trText("label_username"));
  m_oldLabel->setText(trText("label_old_pass"));
  m_newLabel->setText(trText("label_new_pass"));
  m_confirmLabel->setText(trText("label_confirm_new"));
  m_changeBtn->setText(trText("btn_change_pass"));
  m_backBtn->setText(trText("btn_back"));

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
  if (m_oldEdit)
    m_oldEdit->setPlaceholderText(pick(m_lang, "旧密码", "Old Password"));
  if (m_newEdit)
    m_newEdit->setPlaceholderText(pick(m_lang, "新密码", "New Password"));
  if (m_confirmEdit)
    m_confirmEdit->setPlaceholderText(pick(m_lang, "确认新密码", "Confirm New Password"));

  if (m_langLabel)
    m_langLabel->setVisible(true);
  if (m_themeLabel)
    m_themeLabel->setVisible(true);
  if (m_userLabel)
    m_userLabel->setVisible(true);
  if (m_oldLabel)
    m_oldLabel->setVisible(true);
  if (m_newLabel)
    m_newLabel->setVisible(true);
  if (m_confirmLabel)
    m_confirmLabel->setVisible(true);

  if (m_langBtn)
  {
    m_langBtn->adjustSize();
    m_langBtn->updateGeometry();
  }
  if (m_changeBtn)
  {
    m_changeBtn->adjustSize();
    m_changeBtn->updateGeometry();
  }
  if (m_backBtn)
  {
    m_backBtn->adjustSize();
    m_backBtn->updateGeometry();
  }
}

QString ChangePasswordDialog::trText(const QString &key) const
{
  if (key == "cp_title")
    return pick(m_lang, "修改密码", "Change Password");
  if (key == "label_username")
    return pick(m_lang, "用户名:", "Username:");
  if (key == "label_old_pass")
    return pick(m_lang, "旧密码:", "Old Password:");
  if (key == "label_new_pass")
    return pick(m_lang, "新密码:", "New Password:");
  if (key == "label_confirm_new")
    return pick(m_lang, "确认新密码:", "Confirm New Password:");
  if (key == "btn_change_pass")
    return pick(m_lang, "修改密码", "Change Password");
  if (key == "btn_back")
    return pick(m_lang, "返回", "Back");
  if (key == "label_language")
    return pick(m_lang, "语言", "Language");
  if (key == "lang_switch")
    return pick(m_lang, "English", "中文");
  if (key == "label_theme")
    return pick(m_lang, "主题", "Theme");
  return key;
}
