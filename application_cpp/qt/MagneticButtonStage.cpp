#include "MagneticButtonStage.h"

#include <QGraphicsDropShadowEffect>
#include <QMouseEvent>
#include <QPushButton>

#include "AppConfig.h"

MagneticButtonStage::MagneticButtonStage(QWidget *parent) : QWidget(parent)
{
  setMouseTracking(true);
  setAttribute(Qt::WA_Hover, true);
  setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Fixed);

  m_anim = new QPropertyAnimation(this);
  m_anim->setTargetObject(nullptr);
  m_anim->setPropertyName("pos");
  m_anim->setDuration(120);

  m_shadow = new QGraphicsDropShadowEffect(this);
  m_shadow->setOffset(0, 10);
  m_shadow->setBlurRadius(30);
  m_shadow->setColor(QColor(0, 0, 0, 89));
  setGraphicsEffect(m_shadow);

  m_shadowBlur = new QPropertyAnimation(m_shadow, "blurRadius", this);
  m_shadowBlur->setDuration(160);
  m_shadowColor = new QPropertyAnimation(m_shadow, "color", this);
  m_shadowColor->setDuration(160);
}

void MagneticButtonStage::setShadowEnabled(bool enabled)
{
  if (m_shadowEnabled == enabled)
    return;
  m_shadowEnabled = enabled;

  if (!m_shadowEnabled)
  {
    if (m_shadowBlur && m_shadowBlur->state() == QAbstractAnimation::Running)
      m_shadowBlur->stop();
    if (m_shadowColor && m_shadowColor->state() == QAbstractAnimation::Running)
      m_shadowColor->stop();
    setGraphicsEffect(nullptr);
    return;
  }

  if (m_shadow)
    setGraphicsEffect(m_shadow);
}

bool MagneticButtonStage::shadowEnabled() const { return m_shadowEnabled; }

void MagneticButtonStage::setButton(QPushButton *button)
{
  if (m_button == button)
    return;
  if (m_button)
  {
    m_button->setParent(nullptr);
  }
  m_button = button;
  if (m_button)
  {
    m_button->setParent(this);
    m_button->raise();
    m_button->move(centerPos());
    m_anim->setTargetObject(m_button);
  }
  else
  {
    m_anim->setTargetObject(nullptr);
  }
}

QPushButton *MagneticButtonStage::button() const { return m_button; }

QPoint MagneticButtonStage::centerPos() const
{
  if (!m_button)
    return QPoint(0, 0);
  const int x = (width() - m_button->width()) / 2;
  const int y = (height() - m_button->height()) / 2;
  return QPoint(x, y);
}

void MagneticButtonStage::resizeEvent(QResizeEvent *event)
{
  QWidget::resizeEvent(event);
  if (!m_button)
    return;
  moveButtonTo(centerPos(), false);
}

void MagneticButtonStage::enterEvent(QEnterEvent *event)
{
  QWidget::enterEvent(event);
  if (!m_shadowEnabled || !m_shadow)
    return;
  if (m_shadowBlur->state() == QAbstractAnimation::Running)
    m_shadowBlur->stop();
  if (m_shadowColor->state() == QAbstractAnimation::Running)
    m_shadowColor->stop();

  m_shadowBlur->setStartValue(m_shadow->blurRadius());
  m_shadowBlur->setEndValue(36.0);
  m_shadowBlur->start();

  QColor glow = AppConfig::effectsAccent();
  glow.setAlpha(89);
  m_shadowColor->setStartValue(m_shadow->color());
  m_shadowColor->setEndValue(glow);
  m_shadowColor->start();
}

void MagneticButtonStage::leaveEvent(QEvent *event)
{
  QWidget::leaveEvent(event);
  if (!m_button)
    return;
  moveButtonTo(centerPos(), true);

  if (!m_shadowEnabled || !m_shadow)
    return;
  if (m_shadowBlur->state() == QAbstractAnimation::Running)
    m_shadowBlur->stop();
  if (m_shadowColor->state() == QAbstractAnimation::Running)
    m_shadowColor->stop();

  m_shadowBlur->setStartValue(m_shadow->blurRadius());
  m_shadowBlur->setEndValue(30.0);
  m_shadowBlur->start();

  QColor base(0, 0, 0, 89);
  m_shadowColor->setStartValue(m_shadow->color());
  m_shadowColor->setEndValue(base);
  m_shadowColor->start();
}

void MagneticButtonStage::mouseMoveEvent(QMouseEvent *event)
{
  QWidget::mouseMoveEvent(event);
  if (!m_button)
    return;

  const QPoint c = rect().center();
  const QPoint p = event->pos();
  const QPoint d = p - c;

  const qreal maxOffset = 10.0;
  const qreal scale = 0.08;
  const qreal ox = qBound(-maxOffset, d.x() * scale, maxOffset);
  const qreal oy = qBound(-maxOffset, d.y() * scale, maxOffset);

  const QPoint target = centerPos() + QPoint(static_cast<int>(qRound(ox)),
                                             static_cast<int>(qRound(oy)));
  moveButtonTo(target, true);
}

void MagneticButtonStage::moveButtonTo(const QPoint &pos, bool animated)
{
  if (!m_button)
    return;
  if (m_lastTarget == pos && animated)
    return;
  m_lastTarget = pos;

  if (!animated)
  {
    if (m_anim->state() == QAbstractAnimation::Running)
    {
      m_anim->stop();
    }
    m_button->move(pos);
    return;
  }

  if (m_anim->targetObject() != m_button)
  {
    m_anim->setTargetObject(m_button);
  }
  if (m_anim->state() == QAbstractAnimation::Running)
  {
    m_anim->stop();
  }
  m_anim->setStartValue(m_button->pos());
  m_anim->setEndValue(pos);
  m_anim->start();
}
