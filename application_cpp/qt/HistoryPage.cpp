#include "HistoryPage.h"

#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QEvent>
#include <QFile>
#include <QFileInfo>
#include <QFrame>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QMouseEvent>
#include <QPainter>
#include <QProcess>
#include <QScrollArea>
#include <QShowEvent>
#include <QTableWidget>
#include <QUrl>
#include <QVariantAnimation>
#include <QVBoxLayout>

#include "AppConfig.h"
#include "NavButton.h"

namespace
{
  QString pick(const QString &lang, const QString &cn, const QString &en)
  {
    return (lang == "EN") ? en : cn;
  }

  QString rgba(const QColor &c, qreal alpha)
  {
    QColor x = c;
    x.setAlphaF(qBound(0.0, alpha, 1.0));
    return QString("rgba(%1,%2,%3,%4)")
        .arg(x.red())
        .arg(x.green())
        .arg(x.blue())
        .arg(QString::number(x.alphaF(), 'f', 3));
  }

  QFrame *sunkenFrame(QWidget *parent)
  {
    class RippleGridFrame final : public QFrame
    {
    public:
      explicit RippleGridFrame(QWidget *p) : QFrame(p) {}

    protected:
      void paintEvent(QPaintEvent *e) override
      {
        QFrame::paintEvent(e);
      }
    };

    auto *f = new RippleGridFrame(parent);
    f->setStyleSheet(
        "QFrame{border-radius:18px;border:1px solid rgba(255,255,255,0.12);background:linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.03));}");
    AppConfig::installGlassCard(f);
    return f;
  }

  class RippleOverlay final : public QWidget
  {
  public:
    explicit RippleOverlay(const QPoint &center, QWidget *parent) : QWidget(parent), m_center(center)
    {
      setAttribute(Qt::WA_TransparentForMouseEvents, true);
      setAttribute(Qt::WA_NoSystemBackground, true);
      setAttribute(Qt::WA_TranslucentBackground, true);
      setGeometry(parent ? parent->rect() : QRect());
    }

    void start()
    {
      auto *a = new QVariantAnimation(this);
      a->setDuration(850);
      a->setStartValue(0.0);
      a->setEndValue(1.0);
      QEasingCurve ease(QEasingCurve::BezierSpline);
      ease.addCubicBezierSegment(QPointF(0.0, 0.0), QPointF(0.58, 1.0), QPointF(1.0, 1.0));
      a->setEasingCurve(ease);
      connect(a, &QVariantAnimation::valueChanged, this, [this](const QVariant &v)
              {
        const qreal t = v.toReal();
        m_t = t;
        update(); });
      connect(a, &QVariantAnimation::finished, this, [this]()
              { close(); });
      a->start(QAbstractAnimation::DeleteWhenStopped);
      show();
      raise();
    }

  protected:
    void paintEvent(QPaintEvent *) override
    {
      QPainter p(this);
      p.setRenderHint(QPainter::Antialiasing, true);

      const qreal scale = 0.7 + (14.0 - 0.7) * m_t;
      const qreal radius = (14.0 * 0.5) * scale;
      const qreal alpha = qBound(0.0, 0.9 * (1.0 - m_t), 0.9);

      QColor edge(103, 209, 255);
      edge.setAlphaF(0.75 * (alpha / 0.9));

      p.setBrush(Qt::NoBrush);
      for (int k = 0; k < 5; ++k)
      {
        const qreal w = 2.0 + static_cast<qreal>(k) * 2.0;
        QColor glow(103, 209, 255);
        glow.setAlphaF((0.25 * (1.0 - static_cast<qreal>(k) / 5.0)) * (alpha / 0.9));
        QPen glowPen(glow);
        glowPen.setWidthF(w);
        glowPen.setCapStyle(Qt::RoundCap);
        glowPen.setJoinStyle(Qt::RoundJoin);
        p.setPen(glowPen);
        p.drawEllipse(QPointF(m_center), radius, radius);
      }

      QPen edgePen(edge);
      edgePen.setWidthF(1.0);
      edgePen.setCapStyle(Qt::RoundCap);
      edgePen.setJoinStyle(Qt::RoundJoin);
      p.setPen(edgePen);
      p.drawEllipse(QPointF(m_center), radius, radius);
    }

  private:
    QPoint m_center;
    qreal m_t = 0.0;
  };

  class TableRippleFilter final : public QObject
  {
  public:
    explicit TableRippleFilter(QWidget *viewport) : QObject(viewport), m_viewport(viewport) {}

  protected:
    bool eventFilter(QObject *watched, QEvent *event) override
    {
      if (!m_viewport || watched != m_viewport)
        return QObject::eventFilter(watched, event);

      if (event->type() == QEvent::MouseButtonPress)
      {
        auto *me = static_cast<QMouseEvent *>(event);
        if (me->button() == Qt::LeftButton)
        {
          auto *r = new RippleOverlay(me->pos(), m_viewport);
          r->start();
        }
      }
      return QObject::eventFilter(watched, event);
    }

  private:
    QWidget *m_viewport = nullptr;
  };

  QDir outputRootDir()
  {
    QDir dataDir(QFileInfo(AppConfig::databaseFilePath()).absolutePath());
    dataDir.cdUp();
    return QDir(dataDir.filePath("output"));
  }

  QDir appCppDir()
  {
    QDir dataDir(QFileInfo(AppConfig::databaseFilePath()).absolutePath());
    dataDir.cdUp();
    return dataDir;
  }

  QString modelScriptPath()
  {
    return appCppDir().filePath("model/model.py");
  }
}

HistoryPage::HistoryPage(QWidget *parent) : QWidget(parent)
{
  auto *root = new QVBoxLayout();
  root->setContentsMargins(0, 0, 0, 0);
  root->setSpacing(0);
  setLayout(root);

  m_scroll = new QScrollArea(this);
  m_scroll->setWidgetResizable(true);
  m_scroll->setFrameShape(QFrame::NoFrame);
  root->addWidget(m_scroll, 1);

  m_content = new QWidget(m_scroll);
  m_scroll->setWidget(m_content);

  auto *vl = new QVBoxLayout();
  vl->setContentsMargins(20, 20, 20, 12);
  vl->setSpacing(0);
  m_content->setLayout(vl);

  auto *header = new QWidget(m_content);
  auto *hl = new QHBoxLayout();
  hl->setContentsMargins(0, 0, 0, 0);
  hl->setSpacing(0);
  header->setLayout(hl);

  m_title = new QLabel(header);
  m_title->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:24px;font-weight:800;}");
  hl->addWidget(m_title, 1);
  vl->addWidget(header);

  vl->addSpacing(20);

  auto *tableWrap = sunkenFrame(m_content);
  auto *cl = new QVBoxLayout();
  cl->setContentsMargins(12, 12, 12, 12);
  cl->setSpacing(0);
  tableWrap->setLayout(cl);

  m_table = new QTableWidget(tableWrap);
  m_table->setColumnCount(3);
  m_table->setRowCount(0);
  m_table->verticalHeader()->setVisible(false);
  m_table->setSelectionBehavior(QAbstractItemView::SelectRows);
  m_table->setSelectionMode(QAbstractItemView::SingleSelection);
  m_table->setEditTriggers(QAbstractItemView::NoEditTriggers);
  m_table->setAlternatingRowColors(false);
  m_table->horizontalHeader()->setStretchLastSection(true);
  m_table->setMouseTracking(true);
  m_table->setFrameShape(QFrame::NoFrame);
  m_table->setShowGrid(false);
  m_table->viewport()->setMouseTracking(true);
  m_table->viewport()->installEventFilter(new TableRippleFilter(m_table->viewport()));
  cl->addWidget(m_table);

  vl->addWidget(tableWrap, 1);
  vl->addSpacing(20);

  auto *btnRow = new QWidget(m_content);
  auto *br = new QHBoxLayout();
  br->setContentsMargins(0, 0, 0, 0);
  br->setSpacing(10);
  btnRow->setLayout(br);

  auto makeBtn = [btnRow]()
  {
    auto *b = new NavButton(btnRow);
    b->setPulseEnabled(true);
    b->setCursor(Qt::PointingHandCursor);
    b->setFlat(true);
    return b;
  };

  m_openFolderBtn = makeBtn();
  m_openFolderBtn->setProperty("i18n_cn", "打开所在文件夹");
  m_openFolderBtn->setProperty("i18n_en", "Open Folder");
  br->addWidget(m_openFolderBtn);

  m_viewReportBtn = makeBtn();
  m_viewReportBtn->setProperty("i18n_cn", "查看报告");
  m_viewReportBtn->setProperty("i18n_en", "View Report");
  br->addWidget(m_viewReportBtn);

  m_refreshBtn = makeBtn();
  m_refreshBtn->setProperty("i18n_cn", "刷新");
  m_refreshBtn->setProperty("i18n_en", "Refresh");
  m_refreshBtn->setProperty("primary", true);
  br->addWidget(m_refreshBtn);
  br->addStretch(1);

  connect(m_openFolderBtn, &QPushButton::clicked, this, [this]()
          { openFolder(); });
  connect(m_viewReportBtn, &QPushButton::clicked, this, [this]()
          { viewReport(); });
  connect(m_refreshBtn, &QPushButton::clicked, this, [this]()
          { loadData(); });

  vl->addWidget(btnRow);
  vl->addSpacing(20);

  m_footer = new QLabel(m_content);
  m_footer->setAlignment(Qt::AlignCenter);
  m_footer->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:12px;}");
  vl->addWidget(m_footer);

  setThemeColor(m_bg);
  setLanguage(m_lang);
  loadData();
}

void HistoryPage::setThemeColor(const QColor &bg)
{
  m_bg = bg;
  setAutoFillBackground(false);
  if (m_content)
    m_content->setAutoFillBackground(false);
  applyTableStyle();
}

void HistoryPage::applyTableStyle()
{
  if (!m_table)
    return;

  const QString accent = AppConfig::effectsAccent().name(QColor::HexRgb);
  const QString selBg = rgba(AppConfig::effectsAccent(), 0.18);

  m_table->setStyleSheet(QString(
                             "QTableWidget{background:transparent;border:0px;color:rgba(255,255,255,0.86);}"
                             "QTableWidget::item{padding:10px 10px;border-bottom:1px solid rgba(255,255,255,0.08);}"
                             "QTableWidget::item:selected{background:%1;color:rgba(255,255,255,0.92);}"
                             "QHeaderView::section{background:rgba(0,0,0,0.18);color:rgba(255,255,255,0.78);font-weight:800;padding:10px 10px;border:0px;border-bottom:1px solid rgba(255,255,255,0.10);}"
                             "QTableCornerButton::section{background:rgba(0,0,0,0.18);border:0px;border-bottom:1px solid rgba(255,255,255,0.10);}")
                             .arg(selBg));

  if (m_table->horizontalHeader())
    m_table->horizontalHeader()->setStyleSheet(QString("QHeaderView{background:transparent;border:0px;}"));

  QPalette pal = m_table->palette();
  pal.setColor(QPalette::Base, QColor(0, 0, 0, 0));
  pal.setColor(QPalette::AlternateBase, QColor(0, 0, 0, 0));
  pal.setColor(QPalette::Text, AppConfig::effectsText());
  pal.setColor(QPalette::Highlight, QColor(accent));
  pal.setColor(QPalette::HighlightedText, AppConfig::effectsText());
  m_table->setPalette(pal);

  auto *viewport = m_table->viewport();
  if (viewport)
  {
    viewport->setStyleSheet(QString("QWidget{background:transparent;border:0px;}"));
  }
}

void HistoryPage::setLanguage(const QString &lang)
{
  m_lang = (lang == "EN") ? "EN" : "CN";

  m_title->setText(pick(m_lang, "历史记录", "History Records"));
  m_footer->setText(pick(m_lang, "© LPDP-RiR 智能医疗平台", "© LPDP-RiR Intelligent Medical Platform"));

  const auto labels = findChildren<QLabel *>();
  for (auto *w : labels)
  {
    const QVariant cn = w->property("i18n_cn");
    const QVariant en = w->property("i18n_en");
    if (cn.isValid() && en.isValid())
    {
      w->setText(pick(m_lang, cn.toString(), en.toString()));
    }
  }
  const auto buttons = findChildren<QPushButton *>();
  for (auto *b : buttons)
  {
    const QVariant cn = b->property("i18n_cn");
    const QVariant en = b->property("i18n_en");
    if (cn.isValid() && en.isValid())
    {
      b->setText(pick(m_lang, cn.toString(), en.toString()));
    }
  }

  if (m_table && m_table->columnCount() == 3)
  {
    m_table->setHorizontalHeaderLabels({
        pick(m_lang, "序号", "ID"),
        pick(m_lang, "记录时间", "Time"),
        pick(m_lang, "文件夹路径", "Path"),
    });
    m_table->setColumnWidth(0, 50);
    m_table->setColumnWidth(1, 160);
    m_table->horizontalHeader()->setStretchLastSection(true);
  }
}

void HistoryPage::loadData()
{
  if (!m_table)
    return;

  m_table->setRowCount(0);

  const QString username = AppConfig::currentUser();
  if (username.trimmed().isEmpty())
    return;

  const auto folders = AppConfig::userHistoryFolders(username);
  const QDir outputRoot = outputRootDir();

  int row = 0;
  for (int i = 0; i < folders.size(); ++i)
  {
    const QString folder = folders[i];
    if (folder.trimmed().isEmpty())
      continue;

    QString displayTime = folder;
    const QDateTime dt = QDateTime::fromString(folder, "yyyyMMdd_HHmmss");
    if (dt.isValid())
      displayTime = dt.toString("yyyy-MM-dd HH:mm:ss");

    const QString fullPath = outputRoot.filePath(folder);
    const bool exists = QFileInfo::exists(fullPath);
    const QString showPath = exists ? fullPath : (fullPath + " [Missing]");

    m_table->insertRow(row);
    m_table->setItem(row, 0, new QTableWidgetItem(QString::number(row + 1)));
    m_table->setItem(row, 1, new QTableWidgetItem(displayTime));
    m_table->setItem(row, 2, new QTableWidgetItem(showPath));
    ++row;
  }
}

QString HistoryPage::selectedFolderPath(bool *isMissing) const
{
  if (isMissing)
    *isMissing = false;
  if (!m_table)
    return QString();

  const auto sel = m_table->selectionModel();
  if (!sel || !sel->hasSelection())
  {
    AppConfig::showToast(
        const_cast<HistoryPage *>(this),
        pick(m_lang, QStringLiteral("提示"), QStringLiteral("Info")),
        pick(m_lang, QStringLiteral("请先选择一条记录"),
             QStringLiteral("Please select a record first")));
    return QString();
  }

  const QModelIndexList rows = sel->selectedRows();
  if (rows.isEmpty())
    return QString();
  const int r = rows.first().row();
  auto *it = m_table->item(r, 2);
  if (!it)
    return QString();

  QString pathStr = it->text();
  if (pathStr.endsWith(" [Missing]"))
  {
    if (isMissing)
      *isMissing = true;
    pathStr.chop(QString(" [Missing]").size());
  }
  return pathStr.trimmed();
}

void HistoryPage::openFolder()
{
  bool missing = false;
  const QString pathStr = selectedFolderPath(&missing);
  if (pathStr.isEmpty())
    return;
  if (!QFileInfo::exists(pathStr))
  {
    AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                         pick(m_lang, QStringLiteral("文件夹不存在"),
                              QStringLiteral("Folder does not exist")));
    return;
  }
  QDesktopServices::openUrl(QUrl::fromLocalFile(pathStr));
}

void HistoryPage::viewReport()
{
  const QString pathStr = selectedFolderPath();
  if (pathStr.isEmpty())
    return;
  const QString reportPath = QDir(pathStr).filePath("report.html");
  if (!QFileInfo::exists(reportPath))
  {
    if (!m_proc)
    {
      m_proc = new QProcess(this);
      connect(m_proc, &QProcess::readyReadStandardError, this, [this]()
              {
                const QString err = QString::fromUtf8(m_proc->readAllStandardError()).trimmed();
                if (!err.isEmpty())
                {
                  AppConfig::showToast(this, pick(m_lang, QStringLiteral("日志"), QStringLiteral("Log")),
                                       err.left(180), 2400);
                } });
      connect(m_proc, &QProcess::finished, this,
              [this](int exitCode, QProcess::ExitStatus exitStatus)
              {
                const bool ok = (exitStatus == QProcess::NormalExit && exitCode == 0);
                if (!ok)
                {
                  AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                                       pick(m_lang, QStringLiteral("生成报告失败，请检查日志。"),
                                            QStringLiteral("Failed to generate report. Please check logs.")),
                                       4200);
                  m_openReportAfterRun = false;
                  m_pendingOutputDir.clear();
                  return;
                }

                if (m_openReportAfterRun && !m_pendingOutputDir.trimmed().isEmpty())
                {
                  m_openReportAfterRun = false;
                  const QString html = QDir(m_pendingOutputDir).filePath("report.html");
                  m_pendingOutputDir.clear();
                  if (QFileInfo::exists(html))
                  {
                    QDesktopServices::openUrl(QUrl::fromLocalFile(html));
                  }
                  else
                  {
                    AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                                         pick(m_lang, QStringLiteral("未找到报告文件：") + html,
                                              QStringLiteral("Report not found: ") + html));
                  }
                }
              });
    }

    if (m_proc->state() != QProcess::NotRunning)
    {
      AppConfig::showToast(this, pick(m_lang, QStringLiteral("提示"), QStringLiteral("Info")),
                           pick(m_lang, QStringLiteral("当前任务仍在运行。"),
                                QStringLiteral("A task is still running.")),
                           2400);
      return;
    }

    const QString reportJson = QDir(pathStr).filePath("report.json");
    if (!QFileInfo::exists(reportJson))
    {
      AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                           pick(m_lang, QStringLiteral("未找到报告文件：") + reportPath,
                                QStringLiteral("Report not found: ") + reportPath));
      return;
    }

    QFile f(reportJson);
    if (!f.open(QIODevice::ReadOnly))
    {
      AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                           pick(m_lang, QStringLiteral("读取 report.json 失败。"),
                                QStringLiteral("Failed to read report.json.")),
                           4200);
      return;
    }
    const QByteArray raw = f.readAll();
    f.close();

    QJsonParseError pe{};
    const QJsonDocument doc = QJsonDocument::fromJson(raw, &pe);
    if (pe.error != QJsonParseError::NoError || !doc.isObject())
    {
      AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                           pick(m_lang, QStringLiteral("解析 report.json 失败。"),
                                QStringLiteral("Failed to parse report.json.")),
                           4200);
      return;
    }

    const QJsonObject obj = doc.object();
    const QString inputPath = obj.value("input_path").toString();
    const QString inputDir = obj.value("input_dir").toString();
    const double overlayAlpha = obj.value("overlay_alpha").toDouble(0.6);
    const double probThreshold = obj.value("prob_threshold").toDouble(0.5);

    if (inputPath.trimmed().isEmpty())
    {
      AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                           pick(m_lang, QStringLiteral("report.json 缺少 input_path，无法重建报告。"),
                                QStringLiteral("report.json missing input_path; cannot regenerate report.")),
                           4200);
      return;
    }

    const QString script = modelScriptPath();
    if (!QFileInfo::exists(script))
    {
      AppConfig::showToast(this, pick(m_lang, QStringLiteral("错误"), QStringLiteral("Error")),
                           pick(m_lang, QStringLiteral("未找到模型脚本：") + script,
                                QStringLiteral("Model script not found: ") + script),
                           4200);
      return;
    }

    AppConfig::showToast(this, pick(m_lang, QStringLiteral("提示"), QStringLiteral("Info")),
                         pick(m_lang, QStringLiteral("未找到 report.html，正在重建报告…"),
                              QStringLiteral("report.html not found. Regenerating...")),
                         2400);

    QStringList args;
    args << script
         << "--report_only"
         << "--input" << inputPath
         << "--output_dir" << pathStr
         << "--overlay_alpha" << QString::number(overlayAlpha, 'f', 2)
         << "--prob_threshold" << QString::number(probThreshold, 'f', 2);
    if (!inputDir.trimmed().isEmpty())
      args << "--input_dir" << inputDir;

    m_pendingOutputDir = pathStr;
    m_openReportAfterRun = true;
    m_proc->setWorkingDirectory(appCppDir().absolutePath());
    m_proc->start(AppConfig::pythonExecutablePath(), args);
    return;
  }
  QDesktopServices::openUrl(QUrl::fromLocalFile(reportPath));
}

void HistoryPage::showEvent(QShowEvent *event)
{
  QWidget::showEvent(event);
  loadData();
}
