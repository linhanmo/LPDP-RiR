#pragma once

#include <QColor>
#include <QElapsedTimer>
#include <QString>
#include <QVector>
#include <QWidget>

class QLabel;
class QScrollArea;
class QTableWidget;

class HomePage final : public QWidget
{
  Q_OBJECT

public:
  explicit HomePage(QWidget *parent = nullptr);

  void setLanguage(const QString &lang);
  void setThemeColor(const QColor &bg);

signals:
  void navigateRequested(const QString &pageKey);

private:
  void paintEvent(QPaintEvent *event) override;

  QString m_lang = "CN";
  QColor m_bg = QColor("#0B1220");

  QScrollArea *m_scroll = nullptr;
  QWidget *m_content = nullptr;

  QElapsedTimer m_fxClock;

  QLabel *m_title = nullptr;
  QLabel *m_subtitle = nullptr;
  QLabel *m_sectionKeyTitle = nullptr;
  QLabel *m_sectionKeySubtitle = nullptr;
  QLabel *m_sectionWorkflowTitle = nullptr;
  QLabel *m_sectionWorkflowSubtitle = nullptr;
  QLabel *m_sectionAdvTitle = nullptr;
  QLabel *m_sectionAdvSubtitle = nullptr;
  QLabel *m_sectionCoreTitle = nullptr;
  QLabel *m_sectionCoreSubtitle = nullptr;
  QLabel *m_footer = nullptr;

  QTableWidget *m_workflowTable = nullptr;
};
