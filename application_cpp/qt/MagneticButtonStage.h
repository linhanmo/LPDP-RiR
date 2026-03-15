#pragma once

#include <QPoint>
#include <QPropertyAnimation>
#include <QWidget>

class QPushButton;
class QResizeEvent;
class QMouseEvent;
class QEvent;
class QEnterEvent;
class QGraphicsDropShadowEffect;

class MagneticButtonStage final : public QWidget
{
  Q_OBJECT

public:
  explicit MagneticButtonStage(QWidget *parent = nullptr);

  void setButton(QPushButton *button);
  QPushButton *button() const;

  void setShadowEnabled(bool enabled);
  bool shadowEnabled() const;

protected:
  void resizeEvent(QResizeEvent *event) override;
  void mouseMoveEvent(QMouseEvent *event) override;
  void enterEvent(QEnterEvent *event) override;
  void leaveEvent(QEvent *event) override;

private:
  void moveButtonTo(const QPoint &pos, bool animated);
  QPoint centerPos() const;

  QPushButton *m_button = nullptr;
  QPropertyAnimation *m_anim = nullptr;
  QPoint m_lastTarget;
  QGraphicsDropShadowEffect *m_shadow = nullptr;
  QPropertyAnimation *m_shadowBlur = nullptr;
  QPropertyAnimation *m_shadowColor = nullptr;
  bool m_shadowEnabled = true;
};
