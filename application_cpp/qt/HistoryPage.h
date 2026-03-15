#pragma once

#include <QColor>
#include <QString>
#include <QWidget>

class QLabel;
class QScrollArea;
class QTableWidget;
class QPushButton;
class QShowEvent;
class QProcess;

class HistoryPage final : public QWidget
{
  Q_OBJECT

public:
  explicit HistoryPage(QWidget *parent = nullptr);

  void setLanguage(const QString &lang);
  void setThemeColor(const QColor &bg);

protected:
  void showEvent(QShowEvent *event) override;

private:
  void applyTableStyle();
  void loadData();
  QString selectedFolderPath(bool *isMissing = nullptr) const;
  void openFolder();
  void viewReport();

  QString m_lang = "CN";
  QColor m_bg = QColor("#0B1220");

  QScrollArea *m_scroll = nullptr;
  QWidget *m_content = nullptr;
  QLabel *m_title = nullptr;
  QTableWidget *m_table = nullptr;
  QPushButton *m_openFolderBtn = nullptr;
  QPushButton *m_viewReportBtn = nullptr;
  QPushButton *m_refreshBtn = nullptr;
  QLabel *m_footer = nullptr;
  QProcess *m_proc = nullptr;
  bool m_openReportAfterRun = false;
  QString m_pendingOutputDir;
};
