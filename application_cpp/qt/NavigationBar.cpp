#include "NavigationBar.h"

#include <QAction>
#include <QColor>
#include <QComboBox>
#include <QCoreApplication>
#include <QDir>
#include <QEnterEvent>
#include <QFileInfo>
#include <QFrame>
#include <QGraphicsDropShadowEffect>
#include <QHBoxLayout>
#include <QLabel>
#include <QMenu>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QPixmap>
#include <QToolButton>

#include "AppConfig.h"
#include "MagneticButtonStage.h"
#include "NavButton.h"

namespace
{
  QString rgba(const QColor &c, qreal alphaF)
  {
    const qreal a = qBound<qreal>(0.0, alphaF, 1.0);
    return QString("rgba(%1,%2,%3,%4)")
        .arg(c.red())
        .arg(c.green())
        .arg(c.blue())
        .arg(QString::number(a, 'f', 3));
  }

  struct ThemeName
  {
    NavigationBar::TextPair label;
  };

  QVector<ThemeName> themeNames()
  {
    return {
        {{"深空玻璃", "Deep Space Glass"}},
        {{"星云紫光", "Nebula Violet"}},
        {{"极光薄荷", "Aurora Mint"}},
        {{"霓虹玫红", "Neon Pink"}},
        {{"青紫渐变", "Cyan Violet"}},
        {{"深夜模式", "Night Mode"}},
    };
  }

  QString logoPath()
  {
    const QDir base(QCoreApplication::applicationDirPath());
    const QStringList rel = {
        QStringLiteral("logo/logo.png"),
        QStringLiteral("../logo/logo.png"),
        QStringLiteral("../../logo/logo.png"),
        QStringLiteral("../../../logo/logo.png"),
    };
    for (const auto &r : rel)
    {
      const QString p = QDir::cleanPath(base.filePath(r));
      if (QFileInfo::exists(p))
        return p;
    }
    return {};
  }

  class TiltCardStage final : public QWidget
  {
  public:
    explicit TiltCardStage(QWidget *parent = nullptr) : QWidget(parent)
    {
      setMouseTracking(true);
      setAttribute(Qt::WA_Hover, true);
      setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Fixed);

      m_shadow = new QGraphicsDropShadowEffect(this);
      m_shadow->setOffset(0, 18);
      m_shadow->setBlurRadius(40);
      m_shadow->setColor(QColor(0, 0, 0, 89));
      setGraphicsEffect(m_shadow);
    }

    void setButton(NavButton *button)
    {
      if (m_button == button)
        return;
      if (m_button)
        m_button->setParent(nullptr);
      m_button = button;
      if (m_button)
      {
        m_button->setParent(this);
        m_button->raise();
        syncToButton();
        moveButtonToCenter();
      }
    }

    NavButton *button() const { return m_button; }

    void syncToButton()
    {
      if (!m_button)
        return;
      m_button->adjustSize();
      const QSize hint = m_button->sizeHint();
      const int w = hint.width() + 14;
      const int h = qMax(40, hint.height() + 10);
      setMinimumSize(w, h);
      resize(w, h);
      moveButtonToCenter();
    }

    void setActive(bool active)
    {
      if (m_active == active)
        return;
      m_active = active;
      update();
    }

  protected:
    void paintEvent(QPaintEvent *event) override
    {
      Q_UNUSED(event);
      QPainter p(this);
      p.setRenderHint(QPainter::Antialiasing, true);

      const QRectF r = rect().adjusted(0.5, 0.5, -0.5, -0.5);
      const qreal radius = 16.0;

      QPainterPath clip;
      clip.addRoundedRect(r, radius, radius);
      p.setClipPath(clip);

      QColor c1 = AppConfig::effectsAccent();
      QColor c2 = AppConfig::effectsAccent2();
      c1.setAlphaF(m_active ? 0.20 : 0.16);
      c2.setAlphaF(m_active ? 0.16 : 0.12);

      QLinearGradient bg(r.topLeft(), r.bottomRight());
      bg.setColorAt(0.0, c1);
      bg.setColorAt(1.0, c2);
      p.fillPath(clip, bg);

      const QPointF center(r.left() + r.width() * m_mouseN.x(), r.top() + r.height() * m_mouseN.y());
      const qreal glowRadius = qMax(r.width(), r.height()) * 0.95;
      QRadialGradient glow(center, glowRadius);
      QColor g0(255, 255, 255);
      g0.setAlphaF(0.16);
      glow.setColorAt(0.0, g0);
      QColor g1 = g0;
      g1.setAlphaF(0.0);
      glow.setColorAt(0.60, g1);
      p.fillPath(clip, glow);

      p.setClipping(false);

      const QColor border = m_active ? QColor(AppConfig::effectsAccent().red(),
                                              AppConfig::effectsAccent().green(),
                                              AppConfig::effectsAccent().blue(), 89)
                                     : QColor(255, 255, 255, 36);
      QPen pen(border, 1.0);
      p.setPen(pen);
      p.setBrush(Qt::NoBrush);
      p.drawRoundedRect(r, radius, radius);
    }

    void resizeEvent(QResizeEvent *event) override
    {
      QWidget::resizeEvent(event);
      moveButtonToCenter();
    }

    void enterEvent(QEnterEvent *event) override
    {
      QWidget::enterEvent(event);
      m_hover = true;
      update();
    }

    void leaveEvent(QEvent *event) override
    {
      QWidget::leaveEvent(event);
      m_hover = false;
      m_mouseN = QPointF(0.5, 0.5);
      moveButtonToCenter();
      update();
    }

    void mouseMoveEvent(QMouseEvent *event) override
    {
      if (!m_button)
        return;

      const QPointF pos = event->position();
      const qreal nx = qBound(0.0, pos.x() / qMax(1.0, (qreal)width()), 1.0);
      const qreal ny = qBound(0.0, pos.y() / qMax(1.0, (qreal)height()), 1.0);
      m_mouseN = QPointF(nx, ny);

      const QPointF c(width() * 0.5, height() * 0.5);
      const QPointF d = pos - c;
      const qreal maxX = 7.0;
      const qreal maxY = 5.0;
      const qreal dx = qBound(-maxX, d.x() / qMax(1.0, width() * 0.5) * maxX, maxX);
      const qreal dy = qBound(-maxY, d.y() / qMax(1.0, height() * 0.5) * maxY, maxY);

      const QPoint base = centerPos();
      m_button->move(base + QPoint((int)dx, (int)dy));
      update();
    }

  private:
    QPoint centerPos() const
    {
      if (!m_button)
        return QPoint(0, 0);
      const int x = (width() - m_button->width()) / 2;
      const int y = (height() - m_button->height()) / 2;
      return QPoint(x, y);
    }

    void moveButtonToCenter()
    {
      if (!m_button)
        return;
      m_button->move(centerPos());
    }

    NavButton *m_button = nullptr;
    QGraphicsDropShadowEffect *m_shadow = nullptr;
    bool m_active = false;
    bool m_hover = false;
    QPointF m_mouseN = QPointF(0.5, 0.5);
  };
}

NavigationBar::NavigationBar(QWidget *parent) : QWidget(parent)
{
  setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
  setObjectName("navbar");
  setStyleSheet(
      "QWidget#navbar{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:18px;}");
  AppConfig::installGlassCard(this);

  auto *root = new QHBoxLayout();
  root->setContentsMargins(14, 10, 14, 10);
  root->setSpacing(10);
  setLayout(root);

  {
    const QString p = logoPath();
    if (!p.isEmpty())
    {
      QPixmap px(p);
      if (!px.isNull())
      {
        auto *logo = new QLabel(this);
        logo->setObjectName(QStringLiteral("app_logo"));
        logo->setStyleSheet("QLabel#app_logo{background:transparent;border:0px;}");
        logo->setPixmap(px.scaled(26, 26, Qt::KeepAspectRatio, Qt::SmoothTransformation));
        root->addWidget(logo, 0, Qt::AlignLeft | Qt::AlignVCenter);
      }
    }
  }

  auto *spacer = new QWidget(this);
  spacer->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
  root->addWidget(spacer, 1);

  const struct PageItem
  {
    QString key;
    TextPair label;
  } pages[] = {
      {"Homepage", {"主页", "Home"}},
      {"Introduction", {"项目介绍", "Introduction"}},
      {"ModelInterface", {"模型推理", "Model Inference"}},
      {"History", {"历史记录", "History"}},
  };

  for (const auto &p : pages)
  {
    auto *wrap = new TiltCardStage(this);
    wrap->setObjectName("navTilt");

    auto *btn = new NavButton(wrap);
    btn->setObjectName("navButton");
    btn->setText(t(p.label));
    btn->setCursor(Qt::PointingHandCursor);
    btn->setPulseEnabled(true);
    btn->setFlat(true);
    btn->setStyleSheet(
        "QPushButton#navButton{background:transparent;color:rgba(255,255,255,0.92);border:0px;padding:8px 14px;font-weight:800;letter-spacing:0.2px;}"
        "QPushButton#navButton:pressed{color:rgba(255,255,255,0.86);}");

    connect(btn, &QPushButton::clicked, this, [this, pageKey = p.key]()
            { emit navigateTo(pageKey); });

    wrap->setButton(btn);
    wrap->syncToButton();
    root->addWidget(wrap);
    m_buttons.insert(p.key, btn);
    m_wrappers.insert(p.key, wrap);
  }

  m_langLabel = new QLabel(this);
  m_langLabel->setText(t({QStringLiteral("语言"), QStringLiteral("Language")}));
  m_langLabel->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.65);font-size:12px;}");
  root->addWidget(m_langLabel);

  m_langBtn = new NavButton(this);
  m_langBtn->setCursor(Qt::PointingHandCursor);
  m_langBtn->setPulseEnabled(true);
  m_langBtn->setFlat(true);
  m_langBtn->setStyleSheet(
      "QPushButton{background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.92);border:1px solid rgba(255,255,255,0.12);padding:8px 12px;border-radius:12px;font-weight:800;}"
      "QPushButton:hover{background:rgba(255,255,255,0.08);}"
      "QPushButton:pressed{background:rgba(255,255,255,0.04);}");
  connect(m_langBtn, &QPushButton::clicked, this, [this]()
          { emit toggleLanguageRequested(); });
  root->addWidget(m_langBtn);

  m_themeLabel = new QLabel(this);
  m_themeLabel->setText(t({QStringLiteral("主题"), QStringLiteral("Theme")}));
  m_themeLabel->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.65);font-size:12px;}");
  root->addWidget(m_themeLabel);

  m_themeCombo = new QComboBox(this);
  m_themeCombo->setSizeAdjustPolicy(QComboBox::AdjustToContents);
  m_themeCombo->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
  m_themeCombo->setStyleSheet(
      "QComboBox{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:12px;padding:8px 12px;color:rgba(255,255,255,0.92);}"
      "QComboBox:hover{background:rgba(255,255,255,0.08);}"
      "QComboBox QAbstractItemView{background:#0C1426;color:rgba(255,255,255,0.92);border:1px solid rgba(255,255,255,0.12);selection-background-color:rgba(103,209,255,0.14);outline:0px;}");
  rebuildThemeNames();
  connect(m_themeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged), this,
          [this](int idx)
          { emit themeIndexChanged(idx); });
  root->addWidget(m_themeCombo);

  m_userButton = new QToolButton(this);
  m_userButton->setText(QStringLiteral("Unknown User"));
  m_userButton->setPopupMode(QToolButton::InstantPopup);
  m_userButton->setSizePolicy(QSizePolicy::Minimum, QSizePolicy::Fixed);
  m_userButton->setStyleSheet(
      "QToolButton{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:12px;padding:8px 12px;color:rgba(255,255,255,0.92);font-weight:800;}"
      "QToolButton:hover{background:rgba(255,255,255,0.08);}"
      "QToolButton::menu-indicator{image:none;width:0px;height:0px;}");
  auto *menu = new QMenu(m_userButton);
  auto *logoutAction = menu->addAction(t({QStringLiteral("退出登录"), QStringLiteral("Logout")}));
  auto *changePasswordAction =
      menu->addAction(t({QStringLiteral("修改密码"), QStringLiteral("Change Password")}));
  connect(logoutAction, &QAction::triggered, this, [this]()
          { emit logoutRequested(); });
  connect(changePasswordAction, &QAction::triggered, this,
          [this]()
          { emit changePasswordRequested(); });
  m_userButton->setMenu(menu);
  root->addWidget(m_userButton);

  applyButtonStyles();
  setActivePage("Homepage");
  setLanguage(m_lang);
  setUsername(AppConfig::currentUser());
}

QString NavigationBar::t(const TextPair &p) const { return (m_lang == "EN") ? p.en : p.cn; }

void NavigationBar::setLanguage(const QString &lang)
{
  m_lang = (lang == "EN") ? "EN" : "CN";
  for (auto it = m_buttons.begin(); it != m_buttons.end(); ++it)
  {
    if (it.key() == "Homepage")
      it.value()->setText(t({QStringLiteral("主页"), QStringLiteral("Home")}));
    if (it.key() == "Introduction")
      it.value()->setText(t({QStringLiteral("项目介绍"), QStringLiteral("Introduction")}));
    if (it.key() == "ModelInterface")
      it.value()->setText(t({QStringLiteral("模型推理"), QStringLiteral("Model Inference")}));
    if (it.key() == "History")
      it.value()->setText(t({QStringLiteral("历史记录"), QStringLiteral("History")}));

    it.value()->adjustSize();
    it.value()->updateGeometry();
    if (m_wrappers.contains(it.key()) && m_wrappers.value(it.key()))
      static_cast<TiltCardStage *>(m_wrappers.value(it.key()))->syncToButton();
  }

  m_langLabel->setText(t({QStringLiteral("语言"), QStringLiteral("Language")}));
  m_langBtn->setText(t({QStringLiteral("English"), QStringLiteral("中文")}));
  m_themeLabel->setText(t({QStringLiteral("主题"), QStringLiteral("Theme")}));
  if (m_langBtn)
  {
    m_langBtn->adjustSize();
    m_langBtn->updateGeometry();
  }

  rebuildThemeNames();

  if (m_userButton && m_userButton->menu())
  {
    const auto acts = m_userButton->menu()->actions();
    if (acts.size() >= 2)
    {
      acts[0]->setText(t({QStringLiteral("退出登录"), QStringLiteral("Logout")}));
      acts[1]->setText(t({QStringLiteral("修改密码"), QStringLiteral("Change Password")}));
    }
  }
}

void NavigationBar::rebuildThemeNames()
{
  if (!m_themeCombo)
    return;
  const int old = m_themeCombo->currentIndex();
  m_themeCombo->blockSignals(true);
  m_themeCombo->clear();
  const auto list = themeNames();
  for (const auto &n : list)
  {
    m_themeCombo->addItem(t(n.label));
  }
  m_themeCombo->setCurrentIndex(old >= 0 ? old : 1);
  m_themeCombo->blockSignals(false);
  m_themeCombo->setMinimumWidth(0);
  m_themeCombo->setMinimumWidth(m_themeCombo->sizeHint().width());
  m_themeCombo->updateGeometry();
}

void NavigationBar::setThemeColor(const QColor &bg)
{
  m_bg = bg;
  setAutoFillBackground(false);
  applyButtonStyles();
}

void NavigationBar::setUsername(const QString &username)
{
  if (!m_userButton)
    return;
  const QString u = username.trimmed();
  m_userButton->setText(u.isEmpty() ? QStringLiteral("Unknown User") : u);
  m_userButton->adjustSize();
  m_userButton->updateGeometry();
}

void NavigationBar::applyButtonStyles()
{
  if (!m_activePage.trimmed().isEmpty())
    setActivePage(m_activePage);
}

void NavigationBar::setActivePage(const QString &pageKey)
{
  m_activePage = pageKey;
  for (auto it = m_wrappers.begin(); it != m_wrappers.end(); ++it)
  {
    static_cast<TiltCardStage *>(it.value())->setActive(it.key() == pageKey);
  }
}
