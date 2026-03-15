#pragma once

#include <QColor>
#include <QString>
#include <QWidget>

class QLabel;
class QScrollArea;

class IntroductionPage final : public QWidget
{
  Q_OBJECT

public:
  explicit IntroductionPage(QWidget *parent = nullptr);

  void setLanguage(const QString &lang);
  void setThemeColor(const QColor &bg);

private:
  void rebuildTables();

  QString m_lang = "CN";
  QColor m_bg = QColor("#0B1220");

  QScrollArea *m_scroll = nullptr;
  QWidget *m_content = nullptr;
  QWidget *m_tablesHost = nullptr;

  QLabel *m_pageTitle = nullptr;
  QLabel *m_pageSubtitle = nullptr;
  QLabel *m_overviewTitle = nullptr;
  QLabel *m_overviewSubtitle = nullptr;
  QLabel *m_overviewP1 = nullptr;
  QLabel *m_overviewP2 = nullptr;
  QLabel *m_overviewP3 = nullptr;
  QLabel *m_overviewP4 = nullptr;
  QLabel *m_footer = nullptr;
};
