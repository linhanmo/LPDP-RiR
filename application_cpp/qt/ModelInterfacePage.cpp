#include "ModelInterfacePage.h"

#include <QApplication>
#include <QComboBox>
#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QFileDialog>
#include <QFileInfo>
#include <QDialog>
#include <QElapsedTimer>
#include <QFrame>
#include <QGroupBox>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QFont>
#include <QLabel>
#include <QMap>
#include <QPainter>
#include <QProcess>
#include <QPushButton>
#include <QTimer>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QtMath>
#include <QSlider>
#include <QSet>
#include <QTextEdit>
#include <QUrl>
#include <QVBoxLayout>

#include <algorithm>
#include <cmath>

#include "AppConfig.h"
#include "MagneticButtonStage.h"

namespace
{
  QString pick(const QString &lang, const QString &cn, const QString &en)
  {
    return (lang == "EN") ? en : cn;
  }

  QString descText(const QString &lang, const QString &type)
  {
    const QString t = type.trimmed();
    if (t == "overlay")
      return pick(lang, QStringLiteral("叠加图: 原始图像 + 预测掩码 + 概率热力图"),
                  QStringLiteral("Overlay: Original + Mask + Heatmap"));
    if (t == "mask")
      return pick(lang, QStringLiteral("预测掩码: 多类别分割结果 (灰度值对应类别)"),
                  QStringLiteral("Mask: Multi-class Segmentation"));
    if (t == "binary")
      return pick(lang, QStringLiteral("二值化结果: 仅前景/背景 (经过后处理)"),
                  QStringLiteral("Binary: Foreground/Background (Post-processed)"));
    if (t == "color")
      return pick(lang, QStringLiteral("彩色掩码: 不同颜色代表不同类别"),
                  QStringLiteral("Color Mask: Classes by Color"));
    if (t == "prob_c0")
      return pick(lang, QStringLiteral("概率图 (背景): 模型预测为背景的置信度"),
                  QStringLiteral("Prob Map (Background): Confidence"));
    if (t == "prob_c1")
      return pick(lang, QStringLiteral("概率图 (前景): 模型预测为前景的置信度"),
                  QStringLiteral("Prob Map (Foreground): Confidence"));
    if (t.compare(QStringLiteral("ACX-UNET"), Qt::CaseInsensitive) == 0 ||
        t.compare(QStringLiteral("UNET"), Qt::CaseInsensitive) == 0 ||
        t.compare(QStringLiteral("U-NET"), Qt::CaseInsensitive) == 0 ||
        t.startsWith(QStringLiteral("unet"), Qt::CaseInsensitive))
      return pick(lang, QStringLiteral("传统U-Net输出：基于切片输入的分割结果（用于对比）"),
                  QStringLiteral("Traditional U-Net output: segmentation result on slice inputs (for comparison)"));
    return pick(lang, QStringLiteral("请先进行分析..."),
                QStringLiteral("Please analyze first..."));
  }

  QFrame *sunkenFrame(QWidget *parent)
  {
    auto *f = new QFrame(parent);
    f->setStyleSheet(
        "QFrame{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:18px;}");
    AppConfig::installGlassCard(f);
    return f;
  }

  void syncMagStageSize(MagneticButtonStage *stage)
  {
    if (!stage)
      return;
    auto *btn = stage->button();
    if (!btn)
      return;
    btn->adjustSize();
    const QSize hint = btn->sizeHint();
    stage->setFixedSize(hint.width() + 24, hint.height() + 24);
  }

  MagneticButtonStage *magButton(const QString &text, const QString &style, QWidget *parent)
  {
    auto *stage = new MagneticButtonStage(parent);
    auto *btn = new QPushButton(text, stage);
    btn->setCursor(Qt::PointingHandCursor);
    btn->setStyleSheet(style);
    btn->adjustSize();
    stage->setButton(btn);
    stage->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    syncMagStageSize(stage);
    return stage;
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

  class ProgressRingWidget final : public QWidget
  {
  public:
    explicit ProgressRingWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
      setFixedSize(160, 160);
    }

    void setProgress(int cur, int tot)
    {
      m_cur = qMax(0, cur);
      m_tot = qMax(0, tot);
      update();
    }

  protected:
    void paintEvent(QPaintEvent *) override
    {
      QPainter p(this);
      p.setRenderHint(QPainter::Antialiasing, true);

      const qreal w = static_cast<qreal>(width());
      const qreal h = static_cast<qreal>(height());
      const qreal cx = w * 0.5;
      const qreal cy = h * 0.5;
      const qreal minDim = qMin(w, h);
      const qreal r0 = qMax<qreal>(18.0, minDim * 0.36);
      const qreal lw = qMax<qreal>(5.0, qMin<qreal>(10.0, r0 * 0.18));

      const QRectF arcRect(cx - r0, cy - r0, r0 * 2.0, r0 * 2.0);

      QPen pen;
      pen.setWidthF(lw);
      pen.setCapStyle(Qt::RoundCap);
      pen.setJoinStyle(Qt::RoundJoin);

      pen.setColor(QColor(255, 255, 255, 31));
      p.setPen(pen);
      p.drawArc(arcRect, 90 * 16, -360 * 16);

      qreal frac = 0.0;
      if (m_tot > 0)
        frac = qBound<qreal>(0.0, static_cast<qreal>(m_cur) / static_cast<qreal>(m_tot), 1.0);

      QLinearGradient g(QPointF(cx - r0, cy - r0), QPointF(cx + r0, cy + r0));
      g.setColorAt(0.0, QColor(103, 209, 255, 242));
      g.setColorAt(1.0, QColor(155, 123, 255, 235));
      pen.setBrush(g);
      p.setPen(pen);
      p.drawArc(arcRect, 90 * 16, static_cast<int>(-360.0 * 16.0 * frac));

      p.setPen(QColor(255, 255, 255, 224));
      QFont f = font();
      f.setPixelSize(qMax(12, static_cast<int>(qRound(r0 * 0.55))));
      f.setWeight(QFont::DemiBold);
      p.setFont(f);

      QString text;
      if (m_tot > 0)
        text = QString::number(qRound(frac * 100.0)) + "%";
      else
        text = QStringLiteral("0%");

      p.drawText(rect(), Qt::AlignCenter, text);

      if (m_tot > 0)
      {
        p.setPen(QColor(255, 255, 255, 140));
        QFont f2 = font();
        f2.setPixelSize(10);
        f2.setWeight(QFont::Normal);
        p.setFont(f2);
        p.drawText(QRect(0, height() / 2 + 18, width(), 20), Qt::AlignHCenter | Qt::AlignTop,
                   QString("%1/%2").arg(m_cur).arg(m_tot));
      }
    }

  private:
    int m_cur = 0;
    int m_tot = 0;
  };

  class TypingDotsWidget final : public QWidget
  {
  public:
    explicit TypingDotsWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
      setFixedSize(44, 22);
      m_tick = new QTimer(this);
      m_tick->setInterval(16);
      connect(m_tick, &QTimer::timeout, this, [this]()
              { update(); });
      m_clock.start();
      m_tick->start();
    }

  protected:
    void paintEvent(QPaintEvent *) override
    {
      QPainter p(this);
      p.setRenderHint(QPainter::Antialiasing, true);

      const auto bezierY = [](qreal x, qreal x1, qreal y1, qreal x2, qreal y2) -> qreal
      {
        x = qBound<qreal>(0.0, x, 1.0);
        auto sample = [](qreal t, qreal a1, qreal a2) -> qreal
        {
          const qreal inv = 1.0 - t;
          return 3.0 * inv * inv * t * a1 + 3.0 * inv * t * t * a2 + t * t * t;
        };
        auto sampleDeriv = [](qreal t, qreal a1, qreal a2) -> qreal
        {
          const qreal inv = 1.0 - t;
          return 3.0 * inv * inv * a1 + 6.0 * inv * t * (a2 - a1) + 3.0 * t * t * (1.0 - a2);
        };

        qreal t = x;
        for (int i = 0; i < 6; ++i)
        {
          const qreal x2v = sample(t, x1, x2) - x;
          const qreal d = sampleDeriv(t, x1, x2);
          if (qFuzzyIsNull(d))
            break;
          t = qBound<qreal>(0.0, t - x2v / d, 1.0);
        }
        return sample(t, y1, y2);
      };

      const qreal periodMs = 1100.0;
      const qreal t = static_cast<qreal>(m_clock.elapsed());
      const qreal base = std::fmod(t, periodMs) / periodMs;

      const qreal d = 7.0;
      const qreal gap = 6.0;
      const qreal lift = 6.0;
      const qreal cy = height() * 0.5;
      const qreal totalW = (3.0 * d) + (2.0 * gap);
      const qreal startX = ((static_cast<qreal>(width()) - totalW) * 0.5) + (d * 0.5);

      const qreal delays[3] = {0.0, 0.12 / 1.1, 0.24 / 1.1};
      const qreal mult[3] = {1.0, 0.75, 0.62};

      for (int i = 0; i < 3; ++i)
      {
        qreal u = base - delays[i];
        u = u - std::floor(u);
        qreal y = 0.0;
        if (u < 0.5)
        {
          const qreal s = bezierY(u / 0.5, 0.42, 0.0, 0.58, 1.0);
          y = -lift * s;
        }
        else
        {
          const qreal s = bezierY((u - 0.5) / 0.5, 0.42, 0.0, 0.58, 1.0);
          y = -lift * (1.0 - s);
        }

        QColor c(255, 255, 255);
        c.setAlphaF(0.72 * mult[i]);
        p.setPen(Qt::NoPen);
        p.setBrush(c);

        const qreal cx = startX + i * (d + gap);
        p.drawEllipse(QPointF(cx, cy + y), d * 0.5, d * 0.5);
      }
    }

  private:
    QElapsedTimer m_clock;
    QTimer *m_tick = nullptr;
  };

  QDialog *makeGlassPopup(QWidget *anchor)
  {
    QWidget *host = anchor ? anchor->window() : nullptr;
    if (!host)
      host = QApplication::activeWindow();

    auto *dlg = new QDialog(host);
    dlg->setAttribute(Qt::WA_DeleteOnClose, true);
    dlg->setWindowFlags(Qt::Dialog | Qt::FramelessWindowHint);
    dlg->setModal(false);

    auto *outer = new QVBoxLayout();
    outer->setContentsMargins(18, 18, 18, 18);
    outer->setSpacing(0);
    dlg->setLayout(outer);

    auto *panel = new QFrame(dlg);
    panel->setObjectName("popup_panel");
    panel->setStyleSheet(
        "QFrame#popup_panel{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:22px;}");
    AppConfig::installGlassCard(panel);
    outer->addWidget(panel, 1);

    auto *root = new QVBoxLayout();
    root->setContentsMargins(18, 16, 18, 16);
    root->setSpacing(12);
    panel->setLayout(root);

    auto *top = new QHBoxLayout();
    top->setContentsMargins(0, 0, 0, 0);
    top->setSpacing(6);
    top->addStretch(1);

    auto *closeBtn = new QPushButton(panel);
    closeBtn->setCursor(Qt::PointingHandCursor);
    closeBtn->setFlat(true);
    closeBtn->setText(QStringLiteral("×"));
    closeBtn->setStyleSheet(
        "QPushButton{background:transparent;color:rgba(255,255,255,0.65);padding:2px 6px;font-size:18px;font-weight:900;}"
        "QPushButton:hover{color:rgba(255,255,255,0.92);}"
        "QPushButton:pressed{color:rgba(255,255,255,0.80);}");
    QObject::connect(closeBtn, &QPushButton::clicked, dlg, [dlg]()
                     { dlg->close(); });
    top->addWidget(closeBtn, 0, Qt::AlignRight);
    root->addLayout(top);
    return dlg;
  }
}

ModelInterfacePage::ModelInterfacePage(QWidget *parent) : QWidget(parent)
{
  auto *root = new QGridLayout();
  root->setContentsMargins(0, 0, 0, 0);
  root->setHorizontalSpacing(0);
  root->setVerticalSpacing(0);
  setLayout(root);

  auto *btnFrame = new QWidget(this);
  auto *btnL = new QHBoxLayout();
  btnL->setContentsMargins(10, 10, 10, 10);
  btnL->setSpacing(6);
  btnL->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
  btnFrame->setLayout(btnL);

  auto *btnImportStage = magButton("", "", btnFrame);
  btnImportStage->button()->setObjectName("btn_import");
  btnImportStage->button()->setProperty("i18n_cn", "导入数据");
  btnImportStage->button()->setProperty("i18n_en", "Import Data");
  btnL->addWidget(btnImportStage);

  auto *btnAnalyzeStage = magButton("", "", btnFrame);
  btnAnalyzeStage->button()->setObjectName("btn_analyze");
  btnAnalyzeStage->button()->setProperty("i18n_cn", "数据分析");
  btnAnalyzeStage->button()->setProperty("i18n_en", "Analyze Data");
  btnAnalyzeStage->button()->setProperty("primary", true);
  btnL->addWidget(btnAnalyzeStage);

  auto *btnVisualizeStage = magButton("", "", btnFrame);
  btnVisualizeStage->button()->setObjectName("btn_visualize");
  btnVisualizeStage->button()->setProperty("i18n_cn", "3D可视化");
  btnVisualizeStage->button()->setProperty("i18n_en", "3D Visualization");
  btnL->addWidget(btnVisualizeStage);

  auto *btnUnetStage = magButton("", "", btnFrame);
  btnUnetStage->button()->setObjectName("btn_unet");
  btnUnetStage->button()->setProperty("i18n_cn", "传统U-Net分析");
  btnUnetStage->button()->setProperty("i18n_en", "Traditional U-Net");
  btnL->addWidget(btnUnetStage);

  auto *btnExportStage = magButton("", "", btnFrame);
  btnExportStage->button()->setObjectName("btn_export");
  btnExportStage->button()->setProperty("i18n_cn", "导出报告");
  btnExportStage->button()->setProperty("i18n_en", "Export Report");
  btnL->addWidget(btnExportStage);

  connect(btnImportStage->button(), &QPushButton::clicked, this, [this]()
          { onImportData(); });
  connect(btnAnalyzeStage->button(), &QPushButton::clicked, this, [this]()
          { onAnalyzeData(); });
  connect(btnVisualizeStage->button(), &QPushButton::clicked, this, [this]()
          { emit visualize3DRequested(m_inputPath); });
  connect(btnUnetStage->button(), &QPushButton::clicked, this, [this]()
          { onUnetAnalysis(); });
  connect(btnExportStage->button(), &QPushButton::clicked, this, [this]()
          { onExportReport(); });

  root->addWidget(btnFrame, 0, 0);

  auto *midFrame = new QWidget(this);
  auto *mid = new QGridLayout();
  mid->setContentsMargins(10, 5, 10, 5);
  mid->setHorizontalSpacing(4);
  mid->setVerticalSpacing(2);
  midFrame->setLayout(mid);

  auto *inHeader = new QWidget(midFrame);
  auto *inHl = new QHBoxLayout();
  inHl->setContentsMargins(2, 0, 2, 2);
  inHl->setSpacing(0);
  inHeader->setLayout(inHl);
  auto *inTitle = new QLabel("", inHeader);
  inTitle->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:12px;font-weight:800;}");
  inTitle->setProperty("i18n_cn", "输入数据");
  inTitle->setProperty("i18n_en", "Input Data");
  inHl->addWidget(inTitle);
  mid->addWidget(inHeader, 0, 0);

  auto *outHeader = new QWidget(midFrame);
  auto *outHl = new QHBoxLayout();
  outHl->setContentsMargins(2, 0, 2, 2);
  outHl->setSpacing(0);
  outHeader->setLayout(outHl);
  auto *outTitle = new QLabel("", outHeader);
  outTitle->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:12px;font-weight:800;}");
  outTitle->setProperty("i18n_cn", "输出结果");
  outTitle->setProperty("i18n_en", "Output Result");
  outHl->addWidget(outTitle);
  outHl->addStretch(1);

  m_resultTypeCombo = new QComboBox(outHeader);
  m_resultTypeCombo->setFixedWidth(120);
  m_resultTypeCombo->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);

  auto *resultTypeLabel = new QLabel("", outHeader);
  resultTypeLabel->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.78);font-size:12px;font-weight:700;margin-right:6px;}");
  resultTypeLabel->setProperty("i18n_cn", "结果类型:");
  resultTypeLabel->setProperty("i18n_en", "Result Type:");

  outHl->addWidget(resultTypeLabel);
  outHl->addWidget(m_resultTypeCombo);
  connect(m_resultTypeCombo, &QComboBox::currentIndexChanged, this, [this](int idx)
          { onResultTypeChanged(idx); });
  mid->addWidget(outHeader, 0, 1);

  auto *inputFrame = sunkenFrame(midFrame);
  auto *inL = new QVBoxLayout();
  inL->setContentsMargins(0, 0, 0, 0);
  inL->setSpacing(0);
  inputFrame->setLayout(inL);
  m_inputPreview = new QLabel(inputFrame);
  m_inputPreview->setMinimumHeight(250);
  m_inputPreview->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
  m_inputPreview->setAlignment(Qt::AlignCenter);
  m_inputPreview->setStyleSheet("QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.70);}");
  inL->addWidget(m_inputPreview, 1);
  mid->addWidget(inputFrame, 1, 0);

  auto *outputFrame = sunkenFrame(midFrame);
  auto *outL = new QVBoxLayout();
  outL->setContentsMargins(0, 0, 0, 0);
  outL->setSpacing(0);
  outputFrame->setLayout(outL);
  m_outputPreview = new QLabel(outputFrame);
  m_outputPreview->setMinimumHeight(250);
  m_outputPreview->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
  m_outputPreview->setAlignment(Qt::AlignCenter);
  m_outputPreview->setStyleSheet("QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.70);}");
  outL->addWidget(m_outputPreview, 1);
  mid->addWidget(outputFrame, 1, 1);

  mid->setColumnStretch(0, 1);
  mid->setColumnStretch(1, 1);
  mid->setRowStretch(1, 1);
  root->addWidget(midFrame, 1, 0);
  root->setRowStretch(1, 1);

  auto *ctrlFrame = new QWidget(this);
  auto *ctrl = new QGridLayout();
  ctrl->setContentsMargins(10, 5, 10, 5);
  ctrl->setHorizontalSpacing(10);
  ctrl->setVerticalSpacing(0);
  ctrlFrame->setLayout(ctrl);

  auto *sliderFrame = new QWidget(ctrlFrame);
  auto *sl = new QHBoxLayout();
  sl->setContentsMargins(0, 0, 0, 0);
  sl->setSpacing(5);
  sliderFrame->setLayout(sl);
  auto *sliceLabelTitle = new QLabel("", sliderFrame);
  sliceLabelTitle->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.78);font-size:12px;font-weight:700;}");
  sliceLabelTitle->setProperty("i18n_cn", "切片索引:");
  sliceLabelTitle->setProperty("i18n_en", "Slice Index:");
  sl->addWidget(sliceLabelTitle);

  m_sliceSlider = new QSlider(Qt::Horizontal, sliderFrame);
  m_sliceSlider->setRange(0, 0);
  m_sliceSlider->setStyleSheet("QSlider{margin-left:5px;margin-right:5px;}");
  connect(m_sliceSlider, &QSlider::valueChanged, this, [this](int v)
          { onSliceChanged(v); });
  sl->addWidget(m_sliceSlider, 1);

  m_sliceLabel = new QLabel("0/0", sliderFrame);
  m_sliceLabel->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.78);font-size:12px;font-weight:700;}");
  sl->addWidget(m_sliceLabel);
  ctrl->addWidget(sliderFrame, 0, 0);

  auto *descFrame = new QWidget(ctrlFrame);
  auto *dl = new QHBoxLayout();
  dl->setContentsMargins(0, 0, 0, 0);
  dl->setSpacing(5);
  descFrame->setLayout(dl);
  auto *descTitle = new QLabel("", descFrame);
  descTitle->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.78);font-size:12px;font-weight:700;}");
  descTitle->setProperty("i18n_cn", "结果说明:");
  descTitle->setProperty("i18n_en", "Description:");
  dl->addWidget(descTitle, 0, Qt::AlignVCenter);

  m_resultDesc = new QTextEdit(descFrame);
  m_resultDesc->setReadOnly(true);
  m_resultDesc->setFrameShape(QFrame::NoFrame);
  m_resultDesc->setFocusPolicy(Qt::NoFocus);
  m_resultDesc->setTextInteractionFlags(Qt::NoTextInteraction);
  m_resultDesc->setLineWrapMode(QTextEdit::NoWrap);
  if (m_resultDesc->viewport())
    m_resultDesc->viewport()->setContentsMargins(0, 0, 0, 0);
  m_resultDesc->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
  m_resultDesc->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
  m_resultDesc->document()->setDocumentMargin(0);
  {
    QFont f = m_resultDesc->font();
    f.setPointSize(12);
    f.setWeight(QFont::DemiBold);
    m_resultDesc->setFont(f);
    m_resultDesc->setFixedHeight(QFontMetrics(f).lineSpacing() + 8);
  }
  m_resultDesc->setStyleSheet("QTextEdit{background:transparent;border:0px;padding:0px;color:rgba(255,255,255,0.82);}");
  m_resultDesc->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
  dl->addWidget(m_resultDesc, 1, Qt::AlignVCenter);
  ctrl->addWidget(descFrame, 0, 1);
  ctrl->setColumnStretch(0, 1);
  ctrl->setColumnStretch(1, 1);
  root->addWidget(ctrlFrame, 2, 0);

  auto *reportFrame = new QWidget(this);
  auto *reportL = new QVBoxLayout();
  reportL->setContentsMargins(10, 10, 10, 10);
  reportL->setSpacing(0);
  reportFrame->setLayout(reportL);
  m_reportGroup = new QGroupBox(reportFrame);
  m_reportGroup->setFixedHeight(200);
  m_reportGroup->setStyleSheet(
      "QGroupBox{border:1px solid rgba(255,255,255,0.12);margin-top:8px;background:rgba(255,255,255,0.06);"
      "border-radius:18px;color:rgba(255,255,255,0.86);}"
      "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;}");
  AppConfig::installGlassCard(m_reportGroup);
  auto *repInner = new QVBoxLayout();
  repInner->setContentsMargins(10, 10, 10, 10);
  repInner->setSpacing(0);
  m_reportGroup->setLayout(repInner);
  m_reportText = new QTextEdit(m_reportGroup);
  m_reportText->setReadOnly(true);
  m_reportText->setFont(QFont(QStringLiteral("Consolas"), 10));
  m_reportText->setStyleSheet("QTextEdit{background:transparent;border:0px;color:rgba(255,255,255,0.86);}");
  repInner->addWidget(m_reportText);
  reportL->addWidget(m_reportGroup);
  root->addWidget(reportFrame, 3, 0);

  auto *footerFrame = new QWidget(this);
  auto *footerL = new QVBoxLayout();
  footerL->setContentsMargins(10, 0, 10, 10);
  footerL->setSpacing(0);
  footerFrame->setLayout(footerL);
  m_footer = new QLabel(footerFrame);
  m_footer->setAlignment(Qt::AlignCenter);
  m_footer->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:12px;}");
  footerL->addWidget(m_footer);
  root->addWidget(footerFrame, 4, 0);

  setThemeColor(m_bg);
  setLanguage(m_lang);
  applyUiState();
  updateResultTypesFromDir();
}

void ModelInterfacePage::setThemeColor(const QColor &bg)
{
  m_bg = bg;
  setAutoFillBackground(false);
}

void ModelInterfacePage::resizeEvent(QResizeEvent *event)
{
  QWidget::resizeEvent(event);
  onSliceChanged(m_sliceSlider ? m_sliceSlider->value() : 0);
}

void ModelInterfacePage::setLanguage(const QString &lang)
{
  m_lang = (lang == "EN") ? "EN" : "CN";

  {
    QFont f = font();
    f.setFamily(m_lang == "EN" ? QStringLiteral("Arial") : QStringLiteral("Microsoft YaHei"));
    setFont(f);
  }

  m_footer->setText(pick(m_lang, "© LPDP-RiR 智能医疗平台", "© LPDP-RiR Intelligent Medical Platform"));
  if (m_reportGroup)
    m_reportGroup->setTitle(pick(m_lang, "报告", "Report"));

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

  const auto stages = findChildren<MagneticButtonStage *>();
  for (auto *s : stages)
    syncMagStageSize(s);

  if (m_resultDesc)
  {
    const QString kind = m_resultTypeCombo ? m_resultTypeCombo->currentData().toString() : QString();
    m_resultDesc->setPlainText(descText(m_lang, kind));
  }

  updatePreviewPlaceholders();
  updateReportSummary();
}

void ModelInterfacePage::updateResultTypesFromDir()
{
  if (!m_resultTypeCombo)
    return;

  const QString prev = m_resultTypeCombo->currentData().toString();
  QStringList types;
  QSet<QString> seen;

  if (!m_outputDir.trimmed().isEmpty() && QDir(m_outputDir).exists())
  {
    QDir d(m_outputDir);
    const QStringList files = d.entryList(QStringList() << "*.png", QDir::Files, QDir::Name);
    for (const QString &fn : files)
    {
      QString stem = fn;
      if (stem.endsWith(".png"))
        stem.chop(4);

      QString type;
      if (stem.startsWith("proc_"))
      {
        const QStringList parts = stem.split('_');
        if (parts.size() >= 3)
          type = parts.mid(2).join('_');
      }
      else if (stem.startsWith("prob_"))
      {
        const int lastUnd = stem.lastIndexOf('_');
        if (lastUnd > 5)
          type = stem.left(lastUnd);
      }
      else if (stem.startsWith("unet_"))
      {
        type = QStringLiteral("ACX-UNET");
      }

      if (type.endsWith("_anno"))
        continue;
      if (!type.isEmpty() && !seen.contains(type))
      {
        seen.insert(type);
        types << type;
      }
    }
  }

  m_resultTypeCombo->blockSignals(true);
  m_resultTypeCombo->clear();
  for (const QString &t : types)
  {
    const QString label = (t == QStringLiteral("ACX-UNET")) ? QStringLiteral("U-Net") : t;
    m_resultTypeCombo->addItem(label, t);
  }

  int idx = -1;
  if (!types.isEmpty())
  {
    if (!prev.isEmpty())
      idx = m_resultTypeCombo->findData(prev);
    if (idx < 0)
      idx = m_resultTypeCombo->findData(QStringLiteral("overlay"));
    if (idx < 0)
      idx = 0;
  }
  m_resultTypeCombo->setCurrentIndex(idx);
  m_resultTypeCombo->blockSignals(false);
  onResultTypeChanged(idx);
}

void ModelInterfacePage::applyUiState()
{
  auto *btnAnalyze = findChild<QPushButton *>(QStringLiteral("btn_analyze"));
  auto *btnExport = findChild<QPushButton *>(QStringLiteral("btn_export"));
  auto *btnUnet = findChild<QPushButton *>(QStringLiteral("btn_unet"));
  const bool idle = (m_proc == nullptr || m_proc->state() == QProcess::NotRunning);
  if (btnAnalyze)
    btnAnalyze->setEnabled(idle);
  if (btnUnet)
    btnUnet->setEnabled(idle);
  if (btnExport)
    btnExport->setEnabled(idle && !m_outputDir.trimmed().isEmpty());
}

void ModelInterfacePage::setOutputDir(const QString &dir)
{
  const QString d = QDir::cleanPath(dir.trimmed());
  if (d == m_outputDir)
    return;
  m_outputDir = d;
  updateResultTypesFromDir();
  updateReportSummary();
  updatePreviewPlaceholders();
  applyUiState();
}

void ModelInterfacePage::updateReportSummary()
{
  if (!m_reportText)
    return;

  if (m_outputDir.trimmed().isEmpty())
  {
    m_reportText->setPlainText(pick(
        m_lang,
        QStringLiteral("报告摘要\n\n请先进行数据分析，生成 report.html 后，这里会展示关键摘要信息。"),
        QStringLiteral("Report Summary\n\nRun analysis to generate report.html, then key fields will be shown here.")));
    return;
  }

  const QString reportHtml = QDir(m_outputDir).filePath("report.html");
  const QString reportJson = QDir(m_outputDir).filePath("report.json");

  if (!QFileInfo::exists(reportJson))
  {
    QStringList lines;
    if (m_lang == "EN")
    {
      lines << QStringLiteral("Report Summary")
            << QString()
            << QStringLiteral("Output: ") + m_outputDir
            << QStringLiteral("Report: ") + (QFileInfo::exists(reportHtml) ? reportHtml : QStringLiteral("N/A"))
            << QString()
            << QStringLiteral("report.json not found. Please export report again.");
    }
    else
    {
      lines << QStringLiteral("报告摘要")
            << QString()
            << QStringLiteral("输出目录：") + m_outputDir
            << QStringLiteral("报告文件：") + (QFileInfo::exists(reportHtml) ? reportHtml : QStringLiteral("N/A"))
            << QString()
            << QStringLiteral("未找到 report.json。可尝试再次导出报告。");
    }
    m_reportText->setPlainText(lines.join('\n'));
    return;
  }

  QFile f(reportJson);
  if (!f.open(QIODevice::ReadOnly))
  {
    const QString err = f.errorString().trimmed();
    if (m_lang == "EN")
      m_reportText->setPlainText(QStringLiteral("Report Summary\n\nFailed to read report.json:\n") + err);
    else
      m_reportText->setPlainText(QStringLiteral("报告摘要\n\n读取 report.json 失败：\n") + err);
    return;
  }

  const QByteArray raw = f.readAll();
  f.close();

  QJsonParseError pe{};
  const QJsonDocument doc = QJsonDocument::fromJson(raw, &pe);
  if (pe.error != QJsonParseError::NoError || !doc.isObject())
  {
    const QString err = pe.errorString().trimmed();
    if (m_lang == "EN")
      m_reportText->setPlainText(QStringLiteral("Report Summary\n\nFailed to read report.json:\n") + err);
    else
      m_reportText->setPlainText(QStringLiteral("报告摘要\n\n读取 report.json 失败：\n") + err);
    return;
  }

  const QJsonObject obj = doc.object();
  const QString ts = obj.value("ts").toString();
  const QString inputPath = obj.value("input_path").toString().trimmed();
  const QJsonArray lesionArr = obj.value("lesion_analyses").toArray();
  const int surgicalPlans = obj.value("surgical_plans_count").toInt(0);

  int high = 0;
  int mid = 0;
  int low = 0;
  QList<double> diameters;
  QMap<QString, int> rads;

  struct LesionRow
  {
    int id = 0;
    double dia = 0.0;
    QString den;
    QString risk;
    QString rec;
  };
  QList<LesionRow> lesions;

  auto shortText = [](QString s, int n) -> QString
  {
    s = s.trimmed();
    s.replace('\n', ' ');
    if (s.size() <= n)
      return s;
    return s.left(n - 1) + QStringLiteral("…");
  };

  for (int i = 0; i < lesionArr.size(); ++i)
  {
    const QJsonObject a = lesionArr.at(i).toObject();
    const QString risk = a.value("risk_level").toString();
    if (risk.contains("Very High") || risk.contains(QStringLiteral("极高")))
      high += 1;
    else if (risk.contains("High") || risk.contains(QStringLiteral("高风险")))
      high += 1;
    else if (risk.contains("Intermediate") || risk.contains(QStringLiteral("中风险")))
      mid += 1;
    else if (risk.contains("Low") || risk.contains(QStringLiteral("低风险")))
      low += 1;

    const double d = a.value("diameter_mm").toDouble(0.0);
    if (d > 0.0)
      diameters.append(d);

    const QString score = a.value("lung_rads_score").toString().trimmed();
    if (!score.isEmpty())
      rads[score] = rads.value(score, 0) + 1;

    LesionRow row;
    row.id = a.value("id").toInt(0);
    row.dia = d;
    row.den = shortText(a.value("density_type").toString(), 28);
    row.risk = shortText(risk, 42);
    row.rec = shortText(a.value("recommendation").toString(), 86);
    lesions.append(row);
  }

  std::sort(lesions.begin(), lesions.end(), [](const LesionRow &a, const LesionRow &b)
            { return a.dia > b.dia; });

  const double maxD = diameters.isEmpty() ? -1.0 : *std::max_element(diameters.begin(), diameters.end());
  double avgD = -1.0;
  if (!diameters.isEmpty())
  {
    double sum = 0.0;
    for (double d : diameters)
      sum += d;
    avgD = sum / double(diameters.size());
  }

  QStringList lines;
  if (m_lang == "EN")
  {
    lines << QStringLiteral("Report Summary")
          << QString()
          << QStringLiteral("Output: ") + m_outputDir
          << QStringLiteral("Report: ") + (QFileInfo::exists(reportHtml) ? reportHtml : QStringLiteral("N/A"));
    if (!ts.trimmed().isEmpty())
      lines << QStringLiteral("Timestamp: ") + ts.trimmed();
    if (!inputPath.isEmpty())
      lines << QStringLiteral("Input: ") + inputPath;
    lines << QString()
          << QStringLiteral("Suspected lesions: %1 (High: %2, Intermediate: %3, Low: %4)")
                 .arg(lesionArr.size())
                 .arg(high)
                 .arg(mid)
                 .arg(low);
    if (maxD >= 0.0)
      lines << QStringLiteral("Max diameter: %1 mm").arg(QString::number(maxD, 'f', 1));
    if (avgD >= 0.0)
      lines << QStringLiteral("Avg diameter: %1 mm").arg(QString::number(avgD, 'f', 1));
    if (!rads.isEmpty())
    {
      QStringList parts;
      const auto keys = rads.keys();
      for (const QString &k : keys)
        parts << (k + QStringLiteral(":") + QString::number(rads.value(k)));
      lines << QStringLiteral("Lung-RADS: ") + parts.join(QStringLiteral(", "));
    }
    lines << QStringLiteral("Surgical plans: %1").arg(surgicalPlans);
    const int topN = qMin(5, lesions.size());
    if (topN > 0)
    {
      lines << QString() << QStringLiteral("Top lesions (by diameter):");
      for (int i = 0; i < topN; ++i)
      {
        const auto &a = lesions.at(i);
        lines << QStringLiteral("- #%1 | %2 mm | %3 | %4")
                     .arg(a.id)
                     .arg(QString::number(a.dia, 'f', 1))
                     .arg(a.den)
                     .arg(a.risk);
        if (!a.rec.isEmpty())
          lines << QStringLiteral("  ") + a.rec;
      }
    }
  }
  else
  {
    lines << QStringLiteral("报告摘要")
          << QString()
          << QStringLiteral("输出目录：") + m_outputDir
          << QStringLiteral("报告文件：") + (QFileInfo::exists(reportHtml) ? reportHtml : QStringLiteral("N/A"));
    if (!ts.trimmed().isEmpty())
      lines << QStringLiteral("时间戳：") + ts.trimmed();
    if (!inputPath.isEmpty())
      lines << QStringLiteral("输入：") + inputPath;
    lines << QString()
          << QStringLiteral("疑似病灶：%1（高风险：%2，中风险：%3，低风险：%4）")
                 .arg(lesionArr.size())
                 .arg(high)
                 .arg(mid)
                 .arg(low);
    if (maxD >= 0.0)
      lines << QStringLiteral("最大直径：%1 mm").arg(QString::number(maxD, 'f', 1));
    if (avgD >= 0.0)
      lines << QStringLiteral("平均直径：%1 mm").arg(QString::number(avgD, 'f', 1));
    if (!rads.isEmpty())
    {
      QStringList parts;
      const auto keys = rads.keys();
      for (const QString &k : keys)
        parts << (k + QStringLiteral(":") + QString::number(rads.value(k)));
      lines << QStringLiteral("Lung-RADS： ") + parts.join(QStringLiteral("，"));
    }
    lines << QStringLiteral("手术规划条目：%1").arg(surgicalPlans);
    const int topN = qMin(5, lesions.size());
    if (topN > 0)
    {
      lines << QString() << QStringLiteral("Top 病灶（按直径排序）：");
      for (int i = 0; i < topN; ++i)
      {
        const auto &a = lesions.at(i);
        lines << QStringLiteral("- #%1 | %2 mm | %3 | %4")
                     .arg(a.id)
                     .arg(QString::number(a.dia, 'f', 1))
                     .arg(a.den)
                     .arg(a.risk);
        if (!a.rec.isEmpty())
          lines << QStringLiteral("  ") + a.rec;
      }
    }
  }

  m_reportText->setPlainText(lines.join('\n'));
}

void ModelInterfacePage::updatePreviewPlaceholders()
{
  if (m_inputPreview)
  {
    m_inputPreview->clear();
    m_inputPreview->setText(QString());
  }
  if (m_outputPreview)
  {
    m_outputPreview->clear();
    m_outputPreview->setText(QString());
  }

  int total = m_totalSlices;
  if (total <= 0 && !m_runInputDir.trimmed().isEmpty())
  {
    QDir d(m_runInputDir);
    const QStringList files = d.entryList(QStringList() << "slice_*.png", QDir::Files);
    total = files.size();
  }

  if (total <= 0)
    total = 0;

  if (m_sliceSlider)
  {
    m_sliceSlider->blockSignals(true);
    m_sliceSlider->setRange(0, total > 0 ? (total - 1) : 0);
    const int cur = qBound(0, m_sliceSlider->value(), total > 0 ? (total - 1) : 0);
    m_sliceSlider->setValue(cur);
    m_sliceSlider->blockSignals(false);
  }

  onSliceChanged(m_sliceSlider ? m_sliceSlider->value() : 0);
}

bool ModelInterfacePage::startModelProcess(const QStringList &args)
{
  const QString script = modelScriptPath();
  if (!QFileInfo::exists(script))
  {
    AppConfig::showToast(this, pick(m_lang, "错误", "Error"),
                         pick(m_lang, "未找到模型脚本：", "Model script not found: ") + script, 4200);
    return false;
  }

  QString actionKey;
  if (args.contains(QStringLiteral("--unet_dir")))
    actionKey = QStringLiteral("unet");
  else if (args.contains(QStringLiteral("--report_only")))
    actionKey = QStringLiteral("export");
  else
    actionKey = QStringLiteral("analyze");

  if (!m_proc)
  {
    m_proc = new QProcess(this);
    AppConfig::configurePythonProcess(m_proc);
    connect(m_proc, &QProcess::readyReadStandardOutput, this, [this]()
            {
      const QString out = QString::fromUtf8(m_proc->readAllStandardOutput());
      const QStringList lines = out.split('\n', Qt::SkipEmptyParts);
      for (const QString &rawLine : lines) {
        const QString line = rawLine.trimmed();
        if (line.startsWith("OUTPUT_DIR:")) {
          setOutputDir(line.mid(QString("OUTPUT_DIR:").size()).trimmed());
        } else if (line.startsWith("INPUT_DIR:")) {
          m_runInputDir = line.mid(QString("INPUT_DIR:").size()).trimmed();
        } else if (line.startsWith("PROGRESS:")) {
          const QString payload = line.mid(QString("PROGRESS:").size()).trimmed();
          const QStringList parts = payload.split('/');
          if (parts.size() == 2) {
            const int cur = parts[0].trimmed().toInt();
            const int tot = parts[1].trimmed().toInt();
            if (tot > 0) {
              m_totalSlices = tot;
              m_progressCur = cur;
              m_progressTot = tot;
              if (!m_progressUiClock.isValid())
                m_progressUiClock.start();
              const qint64 now = m_progressUiClock.elapsed();
              const bool shouldUpdate = (now - m_lastProgressUiMs) >= 80 || cur >= tot;
              if (shouldUpdate)
              {
                m_lastProgressUiMs = now;
                if (m_resultDesc)
                  m_resultDesc->setPlainText(pick(m_lang, "开始分析...", "Starting analysis...") + QString(" %1/%2").arg(cur).arg(tot));
                updatePreviewPlaceholders();
                updateProgressPopup(cur, tot, QString());
              }
            }
          }
        } else if (line.startsWith("PROGRESS_STAGE:")) {
          const QString stage = line.mid(QString("PROGRESS_STAGE:").size()).trimmed();
          if (!m_progressUiClock.isValid())
            m_progressUiClock.start();
          const qint64 now = m_progressUiClock.elapsed();
          const bool shouldUpdate = (now - m_lastProgressUiMs) >= 80 || stage == QStringLiteral("done");
          if (shouldUpdate)
          {
            m_lastProgressUiMs = now;
            if (!stage.isEmpty() && m_resultDesc)
              m_resultDesc->setPlainText(pick(m_lang, "阶段：", "Stage: ") + stage);
            updateProgressPopup(m_progressCur, m_progressTot, stage);
          }
        }
      } });

    connect(m_proc, &QProcess::readyReadStandardError, this, [this]()
            {
      const QString err = QString::fromUtf8(m_proc->readAllStandardError());
      if (!err.trimmed().isEmpty() && m_resultDesc)
        m_resultDesc->setPlainText(pick(m_lang, "日志：", "Log: ") + err.trimmed().left(120)); });

    connect(m_proc, &QProcess::finished, this,
            [this](int exitCode, QProcess::ExitStatus exitStatus)
            {
              const QString doneAction = m_runningActionKey;
              m_runningActionKey.clear();
              const bool ok = (exitStatus == QProcess::NormalExit && exitCode == 0);
              if (m_resultDesc)
                m_resultDesc->setPlainText(ok ? pick(m_lang, "完成", "Done") : pick(m_lang, "失败", "Failed"));
              if (!ok)
              {
                AppConfig::showToast(this, pick(m_lang, "错误", "Error"),
                                     pick(m_lang, "分析失败，请检查日志。", "Analysis failed. Please check logs."),
                                     4200);
              }
              if (ok)
                updateResultTypesFromDir();
              updateReportSummary();
              updatePreviewPlaceholders();
              if (ok)
                onResultTypeChanged(m_resultTypeCombo ? m_resultTypeCombo->currentIndex() : 0);
              applyUiState();
              closeProgressPopup();

              if (ok && (doneAction == QStringLiteral("analyze") || doneAction == QStringLiteral("unet")))
              {
                AppConfig::showToastAction(
                    this, pick(m_lang, QStringLiteral("数据处理完成"), QStringLiteral("Data processing completed")),
                    QString(), QString(), std::function<void()>(), 5000);
              }

              if (doneAction == QStringLiteral("export"))
              {
                if (ok)
                {
                  m_reportHtml = QDir(m_outputDir).filePath("report.html");
                  m_reportReady = true;
                  if (m_typingPopupDone)
                    showReportGeneratedToast(m_reportHtml);
                }
              }
            });
  }

  if (m_proc->state() != QProcess::NotRunning)
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Info"),
                         pick(m_lang, "当前分析仍在运行。", "Analysis is still running."), 2400);
    return false;
  }

  m_totalSlices = 0;
  m_progressCur = 0;
  m_progressTot = 0;
  m_lastProgressUiMs = 0;
  m_progressUiClock.invalidate();
  const QDir wd = appCppDir();
  m_proc->setWorkingDirectory(wd.absolutePath());

  QStringList fullArgs;
  fullArgs << QStringLiteral("-u");
  fullArgs << script;
  fullArgs << args;
  fullArgs << QStringLiteral("--threads") << QString::number(AppConfig::performanceThreads());
  fullArgs << QStringLiteral("--interop_threads") << QString::number(AppConfig::performanceInteropThreads());
  fullArgs << QStringLiteral("--workers") << QString::number(AppConfig::performanceWorkers());

  m_runningActionKey = actionKey;
  if (actionKey == QStringLiteral("analyze") || actionKey == QStringLiteral("unet"))
    showProgressPopup(actionKey);

  m_proc->setProcessEnvironment(AppConfig::pythonProcessEnvironment());
  m_proc->start(AppConfig::pythonExecutablePath(), fullArgs);

  applyUiState();
  return true;
}

void ModelInterfacePage::showProgressPopup(const QString &actionKey)
{
  closeProgressPopup();

  auto *dlg = makeGlassPopup(this);
  dlg->setFixedSize(360, 320);
  m_progressPopup = dlg;
  m_progressTitle = nullptr;
  m_progressSub = nullptr;

  auto *panel = dlg->findChild<QFrame *>(QStringLiteral("popup_panel"));
  auto *root = panel ? qobject_cast<QVBoxLayout *>(panel->layout()) : nullptr;
  if (!root)
  {
    dlg->close();
    m_progressPopup = nullptr;
    return;
  }

  auto *title = new QLabel(dlg);
  title->setAlignment(Qt::AlignHCenter);
  title->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:16px;font-weight:900;}");
  title->setText(actionKey == QStringLiteral("unet") ? pick(m_lang, "传统U-Net分析", "Traditional U-Net")
                                                     : pick(m_lang, "数据分析", "Analyze Data"));
  root->addWidget(title);
  m_progressTitle = title;

  auto *ring = new ProgressRingWidget(dlg);
  ring->setObjectName(QStringLiteral("progress_ring"));
  root->addWidget(ring, 0, Qt::AlignHCenter);
  ring->setProgress(0, 0);
  dlg->setProperty("progress_ring_ptr",
                   QVariant::fromValue<quintptr>(reinterpret_cast<quintptr>(ring)));

  auto *sub = new QLabel(dlg);
  sub->setAlignment(Qt::AlignHCenter);
  sub->setWordWrap(true);
  sub->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:12px;}");
  sub->setText(pick(m_lang, "准备中…", "Preparing..."));
  root->addWidget(sub);
  m_progressSub = sub;

  QWidget *host = window();
  const QPoint topLeft = host ? host->mapToGlobal(QPoint(0, 0)) : QPoint(0, 0);
  const int x = topLeft.x() + (host->width() - dlg->width()) / 2;
  const int y = topLeft.y() + (host->height() - dlg->height()) / 2;
  dlg->move(x, y);
  dlg->show();
  dlg->raise();

  QObject::connect(dlg, &QObject::destroyed, this, [this, dlgPtr = dlg]()
                   {
    if (m_progressPopup != dlgPtr)
      return;
    m_progressPopup = nullptr;
    m_progressTitle = nullptr;
    m_progressSub = nullptr; });
}

void ModelInterfacePage::updateProgressPopup(int cur, int tot, const QString &stage)
{
  if (!m_progressPopup)
    return;

  if (tot > 0)
  {
    m_progressCur = cur;
    m_progressTot = tot;
  }

  const QVariant v = m_progressPopup->property("progress_ring_ptr");
  if (v.isValid())
  {
    auto *ring = reinterpret_cast<ProgressRingWidget *>(v.value<quintptr>());
    if (ring)
      ring->setProgress(m_progressCur, m_progressTot);
  }

  if (m_progressSub)
  {
    QString t = stage.trimmed();
    if (!t.isEmpty() && m_progressTot > 0)
      t = t + QString(" %1/%2").arg(m_progressCur).arg(m_progressTot);
    else if (t.isEmpty() && m_progressTot > 0)
      t = QString("%1/%2").arg(m_progressCur).arg(m_progressTot);
    else if (t.isEmpty())
      t = pick(m_lang, "处理中…", "Processing...");
    m_progressSub->setText(t);
  }
}

void ModelInterfacePage::closeProgressPopup()
{
  if (m_progressPopup)
    m_progressPopup->close();
  m_progressPopup = nullptr;
  m_progressTitle = nullptr;
  m_progressSub = nullptr;
}

void ModelInterfacePage::showTypingPopup()
{
  if (m_typingPopup)
    m_typingPopup->close();

  m_typingPopupDone = false;

  auto *dlg = makeGlassPopup(this);
  dlg->setFixedSize(360, 240);
  m_typingPopup = dlg;

  auto *panel = dlg->findChild<QFrame *>(QStringLiteral("popup_panel"));
  auto *root = panel ? qobject_cast<QVBoxLayout *>(panel->layout()) : nullptr;
  if (!root)
  {
    dlg->close();
    m_typingPopup = nullptr;
    return;
  }

  root->addStretch(2);
  auto *dots = new TypingDotsWidget(dlg);
  dots->setObjectName(QStringLiteral("typing_dots"));
  root->addWidget(dots, 0, Qt::AlignHCenter);

  auto *txt = new QLabel(dlg);
  txt->setAlignment(Qt::AlignHCenter);
  txt->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:13px;font-weight:800;}");
  txt->setText(QStringLiteral("Generating Reports"));
  root->addWidget(txt);
  root->addStretch(1);

  QTimer::singleShot(2000, dlg, [dlg]()
                     {
    if (dlg->isVisible())
      dlg->close(); });

  QWidget *host = window();
  const QPoint topLeft = host ? host->mapToGlobal(QPoint(0, 0)) : QPoint(0, 0);
  const int x = topLeft.x() + (host->width() - dlg->width()) / 2;
  const int y = topLeft.y() + (host->height() - dlg->height()) / 2;
  dlg->move(x, y);
  dlg->show();
  dlg->raise();

  QObject::connect(dlg, &QObject::destroyed, this, [this, dlgPtr = dlg]()
                   {
    if (m_typingPopup != dlgPtr)
      return;
    markTypingPopupDone(); });
}

void ModelInterfacePage::markTypingPopupDone()
{
  m_typingPopup = nullptr;
  m_typingPopupDone = true;
  if (m_reportReady && !m_reportHtml.trimmed().isEmpty())
    showReportGeneratedToast(m_reportHtml);
}

void ModelInterfacePage::showReportGeneratedToast(const QString &reportHtml)
{
  const QString html = QDir::cleanPath(reportHtml.trimmed());
  if (html.isEmpty())
    return;

  AppConfig::showToastAction(
      this, pick(m_lang, QStringLiteral("报告已生成"), QStringLiteral("Report generated")), QString(),
      pick(m_lang, QStringLiteral("打开报告"), QStringLiteral("Open Report")),
      [this, html]()
      {
        if (QFileInfo::exists(html))
          QDesktopServices::openUrl(QUrl::fromLocalFile(html));
        else
          AppConfig::showToast(this, pick(m_lang, "错误", "Error"),
                               pick(m_lang, "未找到报告文件：", "Report not found: ") + html, 4200);
      },
      5000);
}

void ModelInterfacePage::onImportData()
{
  const QString selected = QFileDialog::getOpenFileName(
      this, pick(m_lang, "选择3D数据文件", "Select 3D Data File"), QString(),
      QStringLiteral("Numpy files (*.npy *.npz);;All files (*)"));
  if (selected.isEmpty())
    return;
  m_inputPath = selected;
  m_runInputDir.clear();
  m_outputDir.clear();
  m_totalSlices = 0;
  m_openReportAfterRun = false;
  updateResultTypesFromDir();
  if (m_resultDesc)
    m_resultDesc->setPlainText(descText(m_lang, QString()));
  updateReportSummary();
  updatePreviewPlaceholders();
  applyUiState();

  const QString base = QFileInfo(selected).fileName();
  AppConfig::showToast(this, pick(m_lang, QStringLiteral("导入成功"), QStringLiteral("Imported")),
                       pick(m_lang, QStringLiteral("已加载："), QStringLiteral("Loaded: ")) + base, 2400);
}

void ModelInterfacePage::onAnalyzeData()
{
  const QString input = m_inputPath.trimmed();
  if (input.isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Info"),
                         pick(m_lang, "请先导入数据。", "Please import data first."), 2400);
    return;
  }
  m_openReportAfterRun = false;
  const double a = 0.4;
  const double t = 0.5;
  startModelProcess(QStringList() << "--input" << input << "--overlay_alpha" << QString::number(a, 'f', 2)
                                  << "--prob_threshold" << QString::number(t, 'f', 2));
}

void ModelInterfacePage::onUnetAnalysis()
{
  const QString inDir = m_runInputDir.trimmed();
  if (inDir.isEmpty() || !QDir(inDir).exists())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Info"),
                         pick(m_lang, "请先执行一次分析以生成切片输入。", "Run analysis first to generate input slices."),
                         2600);
    return;
  }
  if (m_outputDir.trimmed().isEmpty() || !QDir(m_outputDir).exists())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Info"),
                         pick(m_lang, "请先执行一次分析以创建输出目录。", "Run analysis first to create output directory."),
                         2600);
    return;
  }

  startModelProcess(QStringList() << "--unet_dir" << inDir << "--unet_out" << m_outputDir);
}

void ModelInterfacePage::onExportReport()
{
  if (m_outputDir.trimmed().isEmpty())
  {
    AppConfig::showToast(this, pick(m_lang, "提示", "Info"),
                         pick(m_lang, "暂无输出目录。", "No output directory."), 2400);
    return;
  }
  const QString reportHtml = QDir(m_outputDir).filePath("report.html");
  if (!QFileInfo::exists(reportHtml))
  {
    const QString input = m_inputPath.trimmed();
    if (input.isEmpty())
    {
      AppConfig::showToast(this, pick(m_lang, "提示", "Info"),
                           pick(m_lang, "请先导入数据。", "Please import data first."), 2400);
      return;
    }

    m_reportReady = false;
    m_reportHtml.clear();
    showTypingPopup();

    const double a = 0.4;
    const double t = 0.5;

    QStringList args;
    args << "--report_only"
         << "--input" << input
         << "--output_dir" << m_outputDir
         << "--overlay_alpha" << QString::number(a, 'f', 2)
         << "--prob_threshold" << QString::number(t, 'f', 2);
    if (!m_runInputDir.trimmed().isEmpty())
      args << "--input_dir" << m_runInputDir;

    if (startModelProcess(args))
    {
      showTypingPopup();
    }
    return;
  }

  m_reportHtml = reportHtml;
  m_reportReady = true;
  showTypingPopup();
}

void ModelInterfacePage::onSliceChanged(int value)
{
  int total = m_totalSlices;
  if (total <= 0 && !m_runInputDir.trimmed().isEmpty())
  {
    QDir d(m_runInputDir);
    total = d.entryList(QStringList() << "slice_*.png", QDir::Files).size();
  }

  const int idx = qBound(0, value, total > 0 ? (total - 1) : 0);
  if (m_sliceLabel)
    m_sliceLabel->setText(QString("%1/%2").arg(total > 0 ? idx + 1 : 0).arg(total));

  QSize target;
  if (m_inputPreview && m_outputPreview)
  {
    target = QSize(qMin(m_inputPreview->width(), m_outputPreview->width()),
                   qMin(m_inputPreview->height(), m_outputPreview->height()));
  }

  if (m_inputPreview)
  {
    if (!m_runInputDir.trimmed().isEmpty())
    {
      const QString inPath = QDir(m_runInputDir).filePath(QString("slice_%1.png").arg(idx, 3, 10, QChar('0')));
      if (QFileInfo::exists(inPath))
      {
        QPixmap px(inPath);
        const QSize s = (target.width() > 0 && target.height() > 0) ? target : m_inputPreview->size();
        m_inputPreview->setPixmap(px.scaled(s, Qt::KeepAspectRatio, Qt::SmoothTransformation));
      }
      else
      {
        m_inputPreview->clear();
        m_inputPreview->setText(QString());
      }
    }
    else
    {
      m_inputPreview->clear();
      m_inputPreview->setText(QString());
    }
  }

  if (m_outputPreview)
  {
    if (!m_outputDir.trimmed().isEmpty())
    {
      const QString kind = m_resultTypeCombo ? m_resultTypeCombo->currentData().toString() : QString();
      QString outPath;
      if (kind == QStringLiteral("ACX-UNET"))
      {
        outPath = QDir(m_outputDir).filePath(QString("unet_%1.png").arg(idx, 3, 10, QChar('0')));
      }
      else if (kind.startsWith("prob_"))
      {
        outPath = QDir(m_outputDir).filePath(QString("%1_%2.png").arg(kind).arg(idx, 3, 10, QChar('0')));
      }
      else if (!kind.trimmed().isEmpty())
      {
        outPath = QDir(m_outputDir).filePath(QString("proc_%1_%2.png").arg(idx, 3, 10, QChar('0')).arg(kind));
      }

      if (QFileInfo::exists(outPath))
      {
        QPixmap px(outPath);
        const QSize s = (target.width() > 0 && target.height() > 0) ? target : m_outputPreview->size();
        m_outputPreview->setPixmap(px.scaled(s, Qt::KeepAspectRatio, Qt::SmoothTransformation));
      }
      else
      {
        m_outputPreview->clear();
        m_outputPreview->setText(QString());
      }
    }
    else
    {
      m_outputPreview->clear();
      m_outputPreview->setText(QString());
    }
  }
}

void ModelInterfacePage::onResultTypeChanged(int)
{
  if (m_resultDesc)
    m_resultDesc->setPlainText(descText(m_lang, m_resultTypeCombo ? m_resultTypeCombo->currentData().toString() : QString()));
  onSliceChanged(m_sliceSlider ? m_sliceSlider->value() : 0);
}
