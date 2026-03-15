#pragma once

#include <QColor>
#include <QElapsedTimer>
#include <QPushButton>
#include <QTimer>

class QPaintEvent;
class QMouseEvent;

class NavButton final : public QPushButton
{
  Q_OBJECT

public:
  explicit NavButton(QWidget *parent = nullptr);

  void setPulseEnabled(bool enabled);
  bool pulseEnabled() const;

protected:
  void paintEvent(QPaintEvent *event) override;
  void mousePressEvent(QMouseEvent *event) override;

private:
  void startPulse();

  bool m_pulseEnabled = false;
  QElapsedTimer m_pulseClock;
  QTimer m_pulseTimer;
  int m_pulseDurationMs = 520;
  QColor m_dotColor = QColor("#475569");
  QColor m_ringColor = QColor("#64748B");
};
