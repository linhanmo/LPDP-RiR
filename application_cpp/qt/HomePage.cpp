#include "HomePage.h"

#include <cmath>
#include <QElapsedTimer>
#include <QFrame>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QPainter>
#include <QTimer>
#include <QPushButton>
#include <QScrollArea>
#include <QTableWidget>
#include <QVBoxLayout>

#include "AppConfig.h"

namespace
{
  QString pick(const QString &lang, const QString &cn, const QString &en)
  {
    return (lang == "EN") ? en : cn;
  }

  QFrame *card(const QString &bg, const QString &border, QWidget *parent)
  {
    auto *c = new QFrame(parent);
    c->setStyleSheet(
        QString("QFrame{background:%1;border:1px solid %2;border-radius:18px;}").arg(bg, border));
    AppConfig::installGlassCard(c);
    return c;
  }

  QWidget *sectionHeader(const QString &bg, const QString &title, const QString &subtitle,
                         QLabel **outTitle, QLabel **outSubtitle, QWidget *parent)
  {
    auto *wrap = new QWidget(parent);
    auto *vl = new QVBoxLayout();
    vl->setContentsMargins(0, 0, 0, 0);
    vl->setSpacing(6);
    wrap->setLayout(vl);

    auto *t = new QLabel(title, wrap);
    t->setStyleSheet(
        "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:20px;font-weight:800;}");
    auto *s = new QLabel(subtitle, wrap);
    s->setWordWrap(true);
    s->setStyleSheet(
        "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.65);font-size:12px;}");
    vl->addWidget(t);
    vl->addWidget(s);

    if (outTitle)
      *outTitle = t;
    if (outSubtitle)
      *outSubtitle = s;

    return wrap;
  }
}

HomePage::HomePage(QWidget *parent) : QWidget(parent)
{
  setAutoFillBackground(false);

  auto *root = new QVBoxLayout();
  root->setContentsMargins(0, 0, 0, 0);
  root->setSpacing(0);
  setLayout(root);

  m_scroll = new QScrollArea(this);
  m_scroll->setWidgetResizable(true);
  m_scroll->setFrameShape(QFrame::NoFrame);
  m_scroll->setStyleSheet(
      "QScrollArea{background:transparent;border:0px;}"
      "QScrollArea QWidget#qt_scrollarea_viewport{background:transparent;}");
  root->addWidget(m_scroll, 1);

  m_content = new QWidget(m_scroll);
  m_scroll->setWidget(m_content);
  m_content->setAutoFillBackground(false);

  if (!m_fxClock.isValid())
    m_fxClock.start();
  auto *fxTimer = new QTimer(this);
  fxTimer->setInterval(50);
  connect(fxTimer, &QTimer::timeout, this, [this]() { update(); });
  fxTimer->start();

  auto *content = new QVBoxLayout();
  content->setContentsMargins(40, 24, 40, 24);
  content->setSpacing(18);
  m_content->setLayout(content);

  auto *hero = new QWidget(m_content);
  auto *heroL = new QVBoxLayout();
  heroL->setContentsMargins(0, 0, 0, 0);
  heroL->setSpacing(10);
  hero->setLayout(heroL);

  m_title = new QLabel(hero);
  m_title->setAlignment(Qt::AlignCenter);
  m_title->setWordWrap(true);
  m_title->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:34px;font-weight:800;}");
  heroL->addWidget(m_title);

  m_subtitle = new QLabel(hero);
  m_subtitle->setAlignment(Qt::AlignCenter);
  m_subtitle->setWordWrap(true);
  m_subtitle->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.65);font-size:22px;}");
  heroL->addWidget(m_subtitle);

  auto *cta = new QHBoxLayout();
  cta->setContentsMargins(0, 0, 0, 0);
  cta->setSpacing(10);
  auto *ctaWrap = new QWidget(hero);
  ctaWrap->setLayout(cta);
  ctaWrap->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
  heroL->addWidget(ctaWrap, 0, Qt::AlignCenter);

  auto *btnPrimary = new QPushButton(hero);
  btnPrimary->setText("");
  btnPrimary->setCursor(Qt::PointingHandCursor);
  btnPrimary->setProperty("primary", true);
  btnPrimary->setStyleSheet("QPushButton{padding:10px 18px;font-weight:800;}");
  cta->addWidget(btnPrimary);
  connect(btnPrimary, &QPushButton::clicked, this,
          [this]()
          { emit navigateRequested(QStringLiteral("ModelInterface")); });

  auto makeSecondary = [hero]()
  {
    auto *b = new QPushButton(hero);
    b->setText("");
    b->setCursor(Qt::PointingHandCursor);
    b->setStyleSheet("QPushButton{padding:10px 18px;font-weight:800;}");
    return b;
  };

  auto *btnSecondary1 = makeSecondary();
  auto *btnSecondary2 = makeSecondary();
  auto *btnSecondary3 = makeSecondary();
  cta->addWidget(btnSecondary1);
  cta->addWidget(btnSecondary2);
  cta->addWidget(btnSecondary3);
  const auto showCtaInfo = [this]()
  {
    AppConfig::showToast(
        this, pick(m_lang, QStringLiteral("提示"), QStringLiteral("Info")),
        pick(m_lang, QStringLiteral("该功能为演示入口，可通过上方导航进入对应模块。"),
             QStringLiteral(
                 "This is a demo entry. Use the top navigation to open the corresponding module.")));
  };
  connect(btnSecondary1, &QPushButton::clicked, this, showCtaInfo);
  connect(btnSecondary2, &QPushButton::clicked, this, showCtaInfo);
  connect(btnSecondary3, &QPushButton::clicked, this, showCtaInfo);

  content->addWidget(hero);

  auto *sec1 = new QWidget(m_content);
  auto *sec1L = new QVBoxLayout();
  sec1L->setContentsMargins(0, 0, 0, 0);
  sec1L->setSpacing(10);
  sec1->setLayout(sec1L);
  sec1L->addWidget(sectionHeader(m_bg.name(), "", "", &m_sectionKeyTitle,
                                 &m_sectionKeySubtitle, sec1));

  auto *grid = new QGridLayout();
  grid->setContentsMargins(0, 0, 0, 0);
  grid->setSpacing(12);

  const struct Metric
  {
    QString value;
    QString cnLabel;
    QString enLabel;
    QString cnNote;
    QString enNote;
  } metrics[] = {
      {"0.9792", "Dice 相似系数（肺结节分割）", "Dice Similarity (Lung Nodule Segmentation)",
       "采用 INT8 量化 + 20% 频域剪枝。", "With INT8 quantization + 20% frequency-domain pruning."},
      {"1.65mm", "HD95", "HD95", "核心分割基准上的 95% Hausdorff 距离。",
       "95% Hausdorff distance on core segmentation benchmarks."},
      {"0.04s", "单例端到端耗时", "Single-Case End-to-End Time", "胸部 CT 工作流对比指标。",
       "Workflow comparison metric for chest CT processing."},
      {"12", "PACS 厂商集成数", "PACS Vendor Integrations", "支持 DICOM 核心服务 + HL7 v2 / HL7 FHIR。",
       "DICOM core services + HL7 v2 / HL7 FHIR support."},
  };

  for (int i = 0; i < 4; ++i)
  {
    auto *c = card("rgba(255,255,255,0.06)", "rgba(255,255,255,0.12)", sec1);
    auto *vl = new QVBoxLayout();
    vl->setContentsMargins(16, 14, 16, 14);
    vl->setSpacing(6);
    c->setLayout(vl);

    auto *v = new QLabel(metrics[i].value, c);
    v->setStyleSheet("QLabel{background:transparent;border:0px;font-size:24px;font-weight:800;}");
    vl->addWidget(v);

    auto *l = new QLabel("", c);
    l->setWordWrap(true);
    l->setStyleSheet("QLabel{background:transparent;border:0px;font-size:12px;font-weight:800;}");
    vl->addWidget(l);

    auto *n = new QLabel("", c);
    n->setWordWrap(true);
    n->setStyleSheet(
        "QLabel{background:transparent;border:0px;font-size:11px;color:rgba(255,255,255,0.65);}");
    vl->addWidget(n);

    grid->addWidget(c, i / 2, i % 2);

    l->setProperty("i18n_cn", metrics[i].cnLabel);
    l->setProperty("i18n_en", metrics[i].enLabel);
    n->setProperty("i18n_cn", metrics[i].cnNote);
    n->setProperty("i18n_en", metrics[i].enNote);
  }

  sec1L->addLayout(grid);
  content->addWidget(sec1);

  auto *secWorkflow = new QWidget(m_content);
  auto *secWorkflowL = new QVBoxLayout();
  secWorkflowL->setContentsMargins(0, 0, 0, 0);
  secWorkflowL->setSpacing(10);
  secWorkflow->setLayout(secWorkflowL);
  secWorkflowL->addWidget(sectionHeader(m_bg.name(), "", "", &m_sectionWorkflowTitle,
                                       &m_sectionWorkflowSubtitle, secWorkflow));

  auto *wfCard = card("rgba(255,255,255,0.06)", "rgba(255,255,255,0.12)", secWorkflow);
  auto *wfL = new QVBoxLayout();
  wfL->setContentsMargins(10, 10, 10, 10);
  wfL->setSpacing(10);
  wfCard->setLayout(wfL);

  m_workflowTable = new QTableWidget(wfCard);
  m_workflowTable->setColumnCount(4);
  m_workflowTable->setRowCount(5);
  m_workflowTable->verticalHeader()->setVisible(false);
  m_workflowTable->setSelectionMode(QAbstractItemView::NoSelection);
  m_workflowTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
  m_workflowTable->setAlternatingRowColors(true);
  m_workflowTable->horizontalHeader()->setStretchLastSection(true);
  m_workflowTable->setStyleSheet(
      "QTableWidget{background:transparent;alternate-background-color:rgba(255,255,255,0.03);border:0px;}"
      "QHeaderView::section{background:rgba(0,0,0,0.18);color:rgba(255,255,255,0.78);font-weight:800;padding:6px;border:0px;border-bottom:1px solid rgba(255,255,255,0.12);}"
      "QTableWidget::item{padding:6px;border-bottom:1px solid rgba(255,255,255,0.06);}");

  const struct WfRow
  {
    QString cnMetric;
    QString enMetric;
    QString manual;
    QString typicalAi;
    QString lpdp;
  } wfRows[] = {
      {QStringLiteral("胸部 CT 单例端到端处理时间"),
       QStringLiteral("Chest CT end-to-end processing time (single case)"),
       QStringLiteral("180–300s"), QStringLiteral("15–30s"), QStringLiteral("0.04s")},
      {QStringLiteral("100 例批处理总耗时"),
       QStringLiteral("100-case batch processing total time"),
       QStringLiteral("50h"), QStringLiteral("50min"), QStringLiteral("<5s")},
      {QStringLiteral("基层肺部疾病误诊率"),
       QStringLiteral("Primary-care lung disease misdiagnosis rate"),
       QStringLiteral("20%–30%"), QStringLiteral("8%–12%"), QStringLiteral("<5%")},
      {QStringLiteral("单例手术路径规划时间"),
       QStringLiteral("Surgical path planning time (single case)"),
       QStringLiteral("30–60min"), QStringLiteral("5–10min"), QStringLiteral("<10s")},
      {QStringLiteral("AR 术中导航静态定位误差"),
       QStringLiteral("AR intraoperative navigation static positioning error"),
       QStringLiteral("-"), QStringLiteral("3–5mm"), QStringLiteral("<1mm")},
  };

  for (int r = 0; r < 5; ++r)
  {
    m_workflowTable->setItem(r, 0,
                             new QTableWidgetItem(pick(m_lang, wfRows[r].cnMetric, wfRows[r].enMetric)));
    m_workflowTable->setItem(r, 1, new QTableWidgetItem(wfRows[r].manual));
    m_workflowTable->setItem(r, 2, new QTableWidgetItem(wfRows[r].typicalAi));
    m_workflowTable->setItem(r, 3, new QTableWidgetItem(wfRows[r].lpdp));
  }
  wfL->addWidget(m_workflowTable);
  secWorkflowL->addWidget(wfCard);
  content->addWidget(secWorkflow);

  auto *sec2 = new QWidget(m_content);
  auto *sec2L = new QVBoxLayout();
  sec2L->setContentsMargins(0, 0, 0, 0);
  sec2L->setSpacing(10);
  sec2->setLayout(sec2L);
  sec2L->addWidget(sectionHeader(m_bg.name(), "", "", &m_sectionAdvTitle,
                                 &m_sectionAdvSubtitle, sec2));

  auto *advGrid = new QGridLayout();
  advGrid->setContentsMargins(0, 0, 0, 0);
  advGrid->setSpacing(12);

  auto makeAdvCard = [sec2](const QString &titleCn, const QString &titleEn,
                            const QVector<QPair<QString, QString>> &items) -> QFrame *
  {
    auto *c = card("rgba(255,255,255,0.06)", "rgba(255,255,255,0.12)", sec2);
    auto *vl = new QVBoxLayout();
    vl->setContentsMargins(16, 14, 16, 14);
    vl->setSpacing(8);
    c->setLayout(vl);

    auto *title = new QLabel("", c);
    title->setStyleSheet("QLabel{background:transparent;border:0px;font-size:12px;font-weight:800;}");
    title->setProperty("i18n_cn", titleCn);
    title->setProperty("i18n_en", titleEn);
    vl->addWidget(title);

    for (const auto &it : items)
    {
      auto *row = new QWidget(c);
      auto *hl = new QHBoxLayout();
      hl->setContentsMargins(0, 0, 0, 0);
      hl->setSpacing(8);
      row->setLayout(hl);

      auto *dot = new QLabel(QStringLiteral("•"), row);
      dot->setStyleSheet(
          "QLabel{background:transparent;border:0px;color:rgba(103,209,255,0.95);font-size:14px;}");
      hl->addWidget(dot);

      auto *txt = new QLabel("", row);
      txt->setWordWrap(true);
      txt->setStyleSheet(
          "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.65);font-size:11px;}");
      txt->setProperty("i18n_cn", it.first);
      txt->setProperty("i18n_en", it.second);
      hl->addWidget(txt, 1);

      vl->addWidget(row);
    }

    return c;
  };

  auto *left = makeAdvCard(
      QStringLiteral("为何选择 LPDP-RiR"),
      QStringLiteral("Why LPDP-RiR"),
      {
          {QStringLiteral("多中心泛化能力强，Dice 相对下降 < 1.2%。"),
           QStringLiteral("Multi-center generalization with <1.2% Dice relative drop.")},
          {QStringLiteral("1000 例连续推理稳定（±0.2% 波动）。"),
           QStringLiteral("Stable inference over 1000 consecutive cases (±0.2% variation).")},
          {QStringLiteral("全面支持 ARM/x86，适配树莓派等轻量场景。"),
           QStringLiteral("Full ARM/x86 support, including lightweight Raspberry Pi scenarios.")},
      });

  auto *right = makeAdvCard(
      QStringLiteral("高级能力设计"),
      QStringLiteral("Advanced by Design"),
      {
          {QStringLiteral("支持 DICOM 核心服务与 HL7 FHIR，适配现代医院工作流。"),
           QStringLiteral("Full DICOM core services and HL7 FHIR support for modern hospital workflows.")},
          {QStringLiteral("快速集成：每家医院 3–7 天（SDK / DICOM 代理，零核心接口改造）。"),
           QStringLiteral("Fast integration: 3–7 days per hospital (SDK / DICOM proxy, zero core-interface refactor).")},
          {QStringLiteral("安全部署：AES-256 与国密级加密方案可选。"),
           QStringLiteral("Security-forward deployment with AES-256 and SM-grade encryption options.")},
      });

  advGrid->addWidget(left, 0, 0);
  advGrid->addWidget(right, 0, 1);
  advGrid->setColumnStretch(0, 1);
  advGrid->setColumnStretch(1, 1);
  sec2L->addLayout(advGrid);
  content->addWidget(sec2);

  auto *sec3 = new QWidget(m_content);
  auto *sec3L = new QVBoxLayout();
  sec3L->setContentsMargins(0, 0, 0, 0);
  sec3L->setSpacing(10);
  sec3->setLayout(sec3L);
  sec3L->addWidget(sectionHeader(m_bg.name(), "", "", &m_sectionCoreTitle,
                                 &m_sectionCoreSubtitle, sec3));

  auto *coreGrid = new QGridLayout();
  coreGrid->setContentsMargins(0, 0, 0, 0);
  coreGrid->setSpacing(12);
  const struct Feature
  {
    QString cnT;
    QString enT;
    QString cnD;
    QString enD;
  } feats[] = {
      {"边缘推理", "Edge Inference", "在边缘设备上实现实时影像分析与辅助诊断。",
       "Real-time image analysis and assisted diagnosis on edge devices."},
      {"一体化工作流", "Integrated Workflow", "统一的影像处理、分析、标注与结果导出能力。",
       "Unified image processing, analysis, annotation, and result export."},
      {"安全与合规", "Security & Compliance", "隐私保护、访问控制与安全的数据传输。",
       "Privacy protection, access control, and secure data transfer."},
  };
  for (int i = 0; i < 3; ++i)
  {
    auto *c = card("rgba(255,255,255,0.06)", "rgba(255,255,255,0.12)", sec3);
    auto *vl = new QVBoxLayout();
    vl->setContentsMargins(16, 14, 16, 14);
    vl->setSpacing(6);
    c->setLayout(vl);
    auto *t = new QLabel("", c);
    t->setStyleSheet("QLabel{background:transparent;border:0px;font-size:12px;font-weight:800;}");
    t->setProperty("i18n_cn", feats[i].cnT);
    t->setProperty("i18n_en", feats[i].enT);
    vl->addWidget(t);
    auto *d = new QLabel("", c);
    d->setWordWrap(true);
    d->setStyleSheet(
        "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.65);font-size:11px;}");
    d->setProperty("i18n_cn", feats[i].cnD);
    d->setProperty("i18n_en", feats[i].enD);
    vl->addWidget(d);
    coreGrid->addWidget(c, 0, i);
  }
  sec3L->addLayout(coreGrid);
  content->addWidget(sec3);

  m_footer = new QLabel(m_content);
  m_footer->setAlignment(Qt::AlignCenter);
  m_footer->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:12px;}");
  content->addWidget(m_footer);

  btnPrimary->setProperty("i18n_cn", "快速开始");
  btnPrimary->setProperty("i18n_en", "Quick Start");
  btnSecondary1->setProperty("i18n_cn", "高级功能");
  btnSecondary1->setProperty("i18n_en", "Advanced Functions");
  btnSecondary2->setProperty("i18n_cn", "账户与帮助");
  btnSecondary2->setProperty("i18n_en", "Account & Get Help");
  btnSecondary3->setProperty("i18n_cn", "论文链接");
  btnSecondary3->setProperty("i18n_en", "Paper Link");

  setThemeColor(m_bg);
  setLanguage(m_lang);
}

void HomePage::setThemeColor(const QColor &bg)
{
  m_bg = bg;
  setAutoFillBackground(false);
  if (m_content)
    m_content->setAutoFillBackground(false);
  update();
}

void HomePage::setLanguage(const QString &lang)
{
  m_lang = (lang == "EN") ? "EN" : "CN";

  m_title->setText(pick(m_lang, "欢迎来到 LPDP-RiR 智能医疗平台",
                        "Welcome to LPDP-RiR Intelligent Medical Platform"));
  m_subtitle->setText(pick(m_lang,
                           "面向边缘设备的行业领先平台，提供影像处理、分析、辅助诊断与治疗一体化能力",
                           "An industry-leading platform for image processing, analysis, auxiliary diagnosis and treatment, tailored for edge devices"));

  m_sectionKeyTitle->setText(pick(m_lang, "关键指标", "Key Metrics"));
  m_sectionKeySubtitle->setText(pick(m_lang, "基于多中心验证、部署测试与工作流对比得到的指标概览。",
                                     "Benchmarks derived from multi-center validation, deployment tests, and workflow comparisons."));

  m_sectionWorkflowTitle->setText(pick(m_lang, "工作流效率", "Workflow Efficiency"));
  m_sectionWorkflowSubtitle->setText(
      pick(m_lang, "跨临床任务的运营影响对比视图。",
           "A compact view of operational impact across clinical tasks."));

  m_sectionAdvTitle->setText(pick(m_lang, "优势", "Advantages"));
  m_sectionAdvSubtitle->setText(pick(m_lang, "强泛化、低硬件要求与快速院内集成。",
                                     "Robust generalization, low hardware requirements, and rapid hospital integration."));

  m_sectionCoreTitle->setText(pick(m_lang, "核心能力", "Core Capabilities"));
  m_sectionCoreSubtitle->setText(pick(m_lang, "从平台视角展示首页核心能力。",
                                      "A platform view of the most visible capabilities on the cover page."));

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

  if (m_workflowTable && m_workflowTable->columnCount() == 4)
  {
    m_workflowTable->setHorizontalHeaderLabels({
        pick(m_lang, "指标", "Metric"),
        pick(m_lang, "人工", "Manual"),
        pick(m_lang, "典型 AI", "Typical AI"),
        pick(m_lang, "LPDP-RiR", "LPDP-RiR"),
    });

    const struct MetricLabel
    {
      QString cn;
      QString en;
    } metrics[] = {
        {QStringLiteral("胸部 CT 单例端到端处理时间"),
         QStringLiteral("Chest CT end-to-end processing time (single case)")},
        {QStringLiteral("100 例批处理总耗时"),
         QStringLiteral("100-case batch processing total time")},
        {QStringLiteral("基层肺部疾病误诊率"),
         QStringLiteral("Primary-care lung disease misdiagnosis rate")},
        {QStringLiteral("单例手术路径规划时间"),
         QStringLiteral("Surgical path planning time (single case)")},
        {QStringLiteral("AR 术中导航静态定位误差"),
         QStringLiteral("AR intraoperative navigation static positioning error")},
    };
    for (int r = 0; r < 5; ++r)
    {
      auto *it = m_workflowTable->item(r, 0);
      if (it)
        it->setText(pick(m_lang, metrics[r].cn, metrics[r].en));
    }
    m_workflowTable->resizeColumnsToContents();
    m_workflowTable->horizontalHeader()->setStretchLastSection(true);
  }
}

void HomePage::paintEvent(QPaintEvent *event)
{
  Q_UNUSED(event);
  QPainter p(this);
  p.setRenderHint(QPainter::Antialiasing, true);
  p.fillRect(rect(), m_bg);

  const qint64 ms = m_fxClock.isValid() ? m_fxClock.elapsed() : 0;
  const qreal phase = (std::sin((ms % 5400) / 5400.0 * 2.0 * 3.14159265358979323846) + 1.0) * 0.5;
  const qreal dx = width() * 0.06 * phase;
  const qreal dy = height() * -0.03 * phase;
  const qreal sc = 1.0 + 0.04 * phase;

  p.save();
  p.translate(width() * 0.5, height() * 0.5);
  p.translate(dx, dy);
  p.scale(sc, sc);
  p.translate(-width() * 0.5, -height() * 0.5);

  p.setCompositionMode(QPainter::CompositionMode_Screen);

  const qreal base = qMin(width(), height());
  const qreal sf = qMax(0.7, base / 780.0);

  auto fillGlow = [&](QPointF center, qreal rx, QColor color, qreal stop)
  {
    QRadialGradient g(center, rx);
    color.setAlphaF(color.alphaF());
    g.setColorAt(0.0, color);
    QColor t = color;
    t.setAlphaF(0.0);
    g.setColorAt(stop, t);
    p.fillRect(rect(), g);
  };

  {
    QColor c(255, 255, 255);
    c.setAlphaF(0.22);
    fillGlow(QPointF(width() * 0.30, height() * 0.30), 240.0 * sf, c, 0.62);
  }
  {
    QColor c(255, 255, 255);
    c.setAlphaF(0.18);
    fillGlow(QPointF(width() * 0.70, height() * 0.30), 250.0 * sf, c, 0.62);
  }
  {
    QColor c = AppConfig::effectsAccent();
    c.setAlphaF(0.22);
    fillGlow(QPointF(width() * 0.50, height() * 1.20), 320.0 * sf, c, 0.64);
  }
  {
    QColor c = AppConfig::effectsAccent2();
    c.setAlphaF(0.18);
    fillGlow(QPointF(width() * 0.50, height() * 1.10), 320.0 * sf, c, 0.68);
  }

  p.restore();
}
