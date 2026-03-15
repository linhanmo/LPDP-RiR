#include "NavButton.h"

#include <QMouseEvent>
#include <QPainter>

#include "AppConfig.h"

NavButton::NavButton(QWidget *parent) : QPushButton(parent)
{
  m_dotColor = AppConfig::effectsAccent();
  m_ringColor = AppConfig::effectsAccent();
  m_pulseTimer.setInterval(16);
  m_pulseTimer.setSingleShot(false);
  connect(&m_pulseTimer, &QTimer::timeout, this, [this]()
          { update(); });
}

void NavButton::setPulseEnabled(bool enabled) { m_pulseEnabled = enabled; }

bool NavButton::pulseEnabled() const { return m_pulseEnabled; }

void NavButton::mousePressEvent(QMouseEvent *event)
{
  if (m_pulseEnabled && event && event->button() == Qt::LeftButton)
  {
    startPulse();
  }
  QPushButton::mousePressEvent(event);
}

void NavButton::startPulse()
{
  m_pulseClock.restart();
  if (!m_pulseTimer.isActive())
  {
    m_pulseTimer.start();
  }
  update();
}

void NavButton::paintEvent(QPaintEvent *event)
{
  QPushButton::paintEvent(event);

  if (!m_pulseEnabled)
  {
    return;
  }
  if (!m_pulseClock.isValid())
  {
    return;
  }

  const qint64 elapsed = m_pulseClock.elapsed();
  if (elapsed < 0)
  {
    return;
  }
  const qreal p = qBound<qreal>(0.0, static_cast<qreal>(elapsed) / m_pulseDurationMs, 1.0);
  if (p >= 1.0)
  {
    if (m_pulseTimer.isActive())
    {
      m_pulseTimer.stop();
    }
    return;
  }

  QPainter painter(this);
  painter.setRenderHint(QPainter::Antialiasing, true);
  painter.setClipRect(rect());

  const qreal w = width();
  const qreal h = height();
  const qreal cx = w * 0.5;
  const qreal cy = h * 0.5;
  const qreal mx = qMin(w, h);

  const qreal dotR = 4.0;
  const qreal ringR = (mx * 0.14) + (mx * 0.42) * (p * p);
  const qreal a = qMax<qreal>(0.0, 1.0 - p);
  const int ringWidth = 1 + static_cast<int>(qRound(2.0 * a));

  QColor dot = AppConfig::effectsAccent();
  dot.setAlpha(180);
  painter.setPen(Qt::NoPen);
  painter.setBrush(dot);
  painter.drawEllipse(QPointF(cx, cy), dotR, dotR);

  QColor ring = AppConfig::effectsAccent();
  ring.setAlpha(static_cast<int>(qRound(170.0 * a)));
  QPen pen(ring, ringWidth);
  painter.setPen(pen);
  painter.setBrush(Qt::NoBrush);
  painter.drawEllipse(QPointF(cx, cy), ringR, ringR);
}
