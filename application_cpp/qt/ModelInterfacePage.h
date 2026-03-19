#pragma once

#include <QColor>
#include <QElapsedTimer>
#include <QString>
#include <QWidget>

class QLabel;
class QComboBox;
class QSlider;
class QTextEdit;
class QProcess;
class QGroupBox;
class QDialog;
class QResizeEvent;

class ModelInterfacePage final : public QWidget
{
  Q_OBJECT

public:
  explicit ModelInterfacePage(QWidget *parent = nullptr);

  void setLanguage(const QString &lang);
  void setThemeColor(const QColor &bg);

protected:
  void resizeEvent(QResizeEvent *event) override;

signals:
  void visualize3DRequested(const QString &suggestedNpzPath);

private:
  void applyUiState();
  void setOutputDir(const QString &dir);
  void updateResultTypesFromDir();
  void updateReportSummary();
  void updatePreviewPlaceholders();
  bool startModelProcess(const QStringList &args);
  void showProgressPopup(const QString &actionKey);
  void updateProgressPopup(int cur, int tot, const QString &stage);
  void closeProgressPopup();
  void showTypingPopup();
  void markTypingPopupDone();
  void showReportGeneratedToast(const QString &reportHtml);

  void onImportData();
  void onAnalyzeData();
  void onUnetAnalysis();
  void onExportReport();
  void onSliceChanged(int value);
  void onResultTypeChanged(int index);

  QString m_lang = "CN";
  QColor m_bg = QColor("#0B1220");

  QLabel *m_footer = nullptr;

  QComboBox *m_resultTypeCombo = nullptr;
  QLabel *m_inputPreview = nullptr;
  QLabel *m_outputPreview = nullptr;
  QSlider *m_sliceSlider = nullptr;
  QLabel *m_sliceLabel = nullptr;
  QTextEdit *m_resultDesc = nullptr;
  QGroupBox *m_reportGroup = nullptr;
  QTextEdit *m_reportText = nullptr;

  QProcess *m_proc = nullptr;
  QString m_inputPath;
  QString m_runInputDir;
  QString m_outputDir;
  int m_totalSlices = 0;
  bool m_openReportAfterRun = false;

  QString m_runningActionKey;

  QDialog *m_progressPopup = nullptr;
  QLabel *m_progressTitle = nullptr;
  QLabel *m_progressSub = nullptr;
  int m_progressCur = 0;
  int m_progressTot = 0;

  QDialog *m_typingPopup = nullptr;
  bool m_typingPopupDone = false;
  bool m_reportReady = false;
  QString m_reportHtml;

  QElapsedTimer m_progressUiClock;
  qint64 m_lastProgressUiMs = 0;
};
