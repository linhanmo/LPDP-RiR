#include "Analyze3DWindow.h"

#include <QButtonGroup>
#include <QComboBox>
#include <QDir>
#include <QFileDialog>
#include <QFileInfo>
#include <QFrame>
#include <QHBoxLayout>
#include <QLabel>
#include <QProcess>
#include <QPushButton>
#include <QRadioButton>
#include <QRegularExpression>
#include <QShortcut>
#include <QVBoxLayout>

#include "AppConfig.h"

#include <QVTKOpenGLNativeWidget.h>
#include <vtkActor.h>
#include <vtkCallbackCommand.h>
#include <vtkCommand.h>
#include <vtkGenericOpenGLRenderWindow.h>
#include <vtkImageCast.h>
#include <vtkImageData.h>
#include <vtkImageImport.h>
#include <vtkImagePlaneWidget.h>
#include <vtkInteractorStyleTrackballCamera.h>
#include <vtkOutlineFilter.h>
#include <vtkPolyDataMapper.h>
#include <vtkRenderWindowInteractor.h>
#include <vtkRenderer.h>
#include <vtkTextProperty.h>
#include <vtkType.h>

#include <zip.h>

#include <algorithm>

namespace
{
  QDir appCppDir()
  {
    QDir dataDir(QFileInfo(AppConfig::databaseFilePath()).absolutePath());
    dataDir.cdUp();
    return dataDir;
  }

  QString repoRootDir()
  {
    QDir d = appCppDir();
    d.cdUp();
    return d.absolutePath();
  }

  QString pythonAnalyzeGuiScript()
  {
    QDir root(repoRootDir());
    const QString p = root.filePath("application_cpp/analyze3D/analyze_gui.py");
    if (QFileInfo::exists(p))
      return p;
    return QString();
  }

  struct NpyData
  {
    QVector<qint64> shape;
    int vtkScalarType = VTK_VOID;
    int elementSizeBytes = 0;
    QByteArray data;
  };

  bool parseNpyHeader(const QByteArray &blob, QString &descr, bool &fortranOrder,
                      QVector<qint64> &shape, int &dataOffset, QString &err)
  {
    if (blob.size() < 12)
    {
      err = QStringLiteral("NPY too small");
      return false;
    }
    if (!(blob[0] == char(0x93) && blob.mid(1, 5) == "NUMPY"))
    {
      err = QStringLiteral("Invalid NPY magic");
      return false;
    }

    const quint8 major = quint8(blob[6]);
    const quint8 minor = quint8(blob[7]);
    Q_UNUSED(minor);

    int headerLen = 0;
    int headerStart = 0;
    if (major == 1)
    {
      headerLen = quint8(blob[8]) | (quint8(blob[9]) << 8);
      headerStart = 10;
    }
    else if (major == 2 || major == 3)
    {
      if (blob.size() < 16)
      {
        err = QStringLiteral("NPY header truncated");
        return false;
      }
      headerLen = int(quint8(blob[8]) | (quint8(blob[9]) << 8) | (quint8(blob[10]) << 16) |
                      (quint8(blob[11]) << 24));
      headerStart = 12;
    }
    else
    {
      err = QStringLiteral("Unsupported NPY version");
      return false;
    }

    if (headerLen <= 0 || headerStart + headerLen > blob.size())
    {
      err = QStringLiteral("Invalid NPY header length");
      return false;
    }

    const QString header = QString::fromLatin1(blob.mid(headerStart, headerLen));
    QRegularExpression reDescr(QStringLiteral(R"((?:'descr'|"descr")\s*:\s*['"]([^'"]+)['"])"));
    QRegularExpression reFortran(QStringLiteral(R"((?:'fortran_order'|"fortran_order")\s*:\s*(True|False))"));
    QRegularExpression reShape(QStringLiteral(R"((?:'shape'|"shape")\s*:\s*\(([^)]*)\))"));

    auto mDescr = reDescr.match(header);
    auto mFortran = reFortran.match(header);
    auto mShape = reShape.match(header);
    if (!mDescr.hasMatch() || !mFortran.hasMatch() || !mShape.hasMatch())
    {
      err = QStringLiteral("Failed to parse NPY header");
      return false;
    }

    descr = mDescr.captured(1);
    fortranOrder = (mFortran.captured(1) == QStringLiteral("True"));

    shape.clear();
    const QStringList parts =
        mShape.captured(1).split(',', Qt::SkipEmptyParts);
    for (const QString &p : parts)
    {
      const QString t = p.trimmed();
      if (t.isEmpty())
        continue;
      bool ok = false;
      const qint64 v = t.toLongLong(&ok);
      if (!ok || v <= 0)
      {
        err = QStringLiteral("Invalid shape in NPY header");
        return false;
      }
      shape.push_back(v);
    }

    if (shape.isEmpty())
    {
      err = QStringLiteral("Empty shape in NPY header");
      return false;
    }

    dataOffset = headerStart + headerLen;
    return true;
  }

  bool dtypeToVtk(const QString &descr, int &vtkScalarType, int &elementSizeBytes)
  {
    if (descr.size() < 3)
      return false;

    const QChar endian = descr[0];
    const QChar kind = descr[1];
    bool ok = false;
    const int size = descr.mid(2).toInt(&ok);
    if (!ok || size <= 0)
      return false;

    Q_UNUSED(endian);
    elementSizeBytes = size;

    if (kind == QChar('f'))
    {
      if (size == 4)
        vtkScalarType = VTK_FLOAT;
      else if (size == 8)
        vtkScalarType = VTK_DOUBLE;
      else
        return false;
      return true;
    }
    if (kind == QChar('i'))
    {
      if (size == 1)
        vtkScalarType = VTK_SIGNED_CHAR;
      else if (size == 2)
        vtkScalarType = VTK_SHORT;
      else if (size == 4)
        vtkScalarType = VTK_INT;
      else if (size == 8)
        vtkScalarType = VTK_LONG_LONG;
      else
        return false;
      return true;
    }
    if (kind == QChar('u'))
    {
      if (size == 1)
        vtkScalarType = VTK_UNSIGNED_CHAR;
      else if (size == 2)
        vtkScalarType = VTK_UNSIGNED_SHORT;
      else if (size == 4)
        vtkScalarType = VTK_UNSIGNED_INT;
      else if (size == 8)
        vtkScalarType = VTK_UNSIGNED_LONG_LONG;
      else
        return false;
      return true;
    }
    if (kind == QChar('b'))
    {
      if (size != 1)
        return false;
      vtkScalarType = VTK_UNSIGNED_CHAR;
      return true;
    }
    return false;
  }

  qint64 product(const QVector<qint64> &v, int startIndex, int count)
  {
    qint64 p = 1;
    for (int i = 0; i < count; ++i)
      p *= v[startIndex + i];
    return p;
  }

  bool reduceTo3D(NpyData &npy, QString &err)
  {
    if (npy.shape.size() == 3)
      return true;

    if (npy.shape.size() < 3)
    {
      err = QStringLiteral("Array is not 3D");
      return false;
    }

    const int dims = npy.shape.size();
    const qint64 last = npy.shape[dims - 1];
    const qint64 first = npy.shape[0];

    const bool channelsLast = (dims == 4 && (last == 1 || last == 3 || last == 4));
    const bool channelsFirst = (dims == 4 && (first == 1 || first == 3 || first == 4));

    if (channelsLast)
    {
      const qint64 d = npy.shape[0];
      const qint64 h = npy.shape[1];
      const qint64 w = npy.shape[2];
      const qint64 c = npy.shape[3];
      const qint64 voxels = d * h * w;
      QByteArray out;
      out.resize(int(voxels * npy.elementSizeBytes));
      const char *src = npy.data.constData();
      char *dst = out.data();
      for (qint64 i = 0; i < voxels; ++i)
      {
        memcpy(dst + i * npy.elementSizeBytes, src + (i * c) * npy.elementSizeBytes, npy.elementSizeBytes);
      }
      npy.data = out;
      npy.shape = {d, h, w};
      return true;
    }

    if (channelsFirst)
    {
      const qint64 c = npy.shape[0];
      Q_UNUSED(c);
      const qint64 d = npy.shape[1];
      const qint64 h = npy.shape[2];
      const qint64 w = npy.shape[3];
      const qint64 voxels = d * h * w;
      QByteArray out;
      out.resize(int(voxels * npy.elementSizeBytes));
      const char *src = npy.data.constData();
      memcpy(out.data(), src, size_t(out.size()));
      npy.data = out;
      npy.shape = {d, h, w};
      return true;
    }

    const qint64 voxels3 = product(npy.shape, dims - 3, 3);
    const qint64 bytes3 = voxels3 * npy.elementSizeBytes;
    if (bytes3 > npy.data.size())
    {
      err = QStringLiteral("Array data truncated");
      return false;
    }
    npy.data = npy.data.left(int(bytes3));
    npy.shape = {npy.shape[dims - 3], npy.shape[dims - 2], npy.shape[dims - 1]};
    return true;
  }

  QStringList listNpzKeys(const QString &npzPath, QString &err)
  {
    int zerr = 0;
    zip_t *za = zip_open(npzPath.toUtf8().constData(), ZIP_RDONLY, &zerr);
    if (!za)
    {
      err = QStringLiteral("Failed to open NPZ");
      return {};
    }

    QStringList keys;
    const zip_int64_t n = zip_get_num_entries(za, 0);
    for (zip_int64_t i = 0; i < n; ++i)
    {
      const char *name = zip_get_name(za, i, 0);
      if (!name)
        continue;
      const QString fn = QString::fromUtf8(name);
      if (!fn.toLower().endsWith(".npy"))
        continue;
      QString k = QFileInfo(fn).completeBaseName();
      if (!k.isEmpty())
        keys << k;
    }
    zip_close(za);
    keys.removeDuplicates();
    keys.sort();
    return keys;
  }

  bool loadNpzEntryAsNpy(const QString &npzPath, const QString &key, NpyData &out, QString &err)
  {
    int zerr = 0;
    zip_t *za = zip_open(npzPath.toUtf8().constData(), ZIP_RDONLY, &zerr);
    if (!za)
    {
      err = QStringLiteral("Failed to open NPZ");
      return false;
    }

    const QString wanted = key + QStringLiteral(".npy");
    zip_int64_t foundIndex = -1;
    const zip_int64_t n = zip_get_num_entries(za, 0);
    for (zip_int64_t i = 0; i < n; ++i)
    {
      const char *name = zip_get_name(za, i, 0);
      if (!name)
        continue;
      const QString fn = QString::fromUtf8(name);
      if (QFileInfo(fn).fileName() == wanted)
      {
        foundIndex = i;
        break;
      }
    }

    if (foundIndex < 0)
    {
      zip_close(za);
      err = QStringLiteral("Key not found in NPZ");
      return false;
    }

    const char *entryName = zip_get_name(za, foundIndex, 0);
    zip_file_t *zf = zip_fopen(za, entryName, 0);
    if (!zf)
    {
      zip_close(za);
      err = QStringLiteral("Failed to read NPZ entry");
      return false;
    }

    QByteArray blob;
    blob.reserve(1024 * 1024);
    char buf[1 << 15];
    while (true)
    {
      const zip_int64_t r = zip_fread(zf, buf, sizeof(buf));
      if (r < 0)
      {
        zip_fclose(zf);
        zip_close(za);
        err = QStringLiteral("Failed to extract NPY");
        return false;
      }
      if (r == 0)
        break;
      blob.append(buf, int(r));
    }

    zip_fclose(zf);
    zip_close(za);

    QString descr;
    bool fortranOrder = false;
    QVector<qint64> shape;
    int dataOffset = 0;
    if (!parseNpyHeader(blob, descr, fortranOrder, shape, dataOffset, err))
      return false;
    if (fortranOrder)
    {
      err = QStringLiteral("Fortran-order arrays are not supported");
      return false;
    }

    int vtkScalarType = VTK_VOID;
    int elementSizeBytes = 0;
    if (!dtypeToVtk(descr, vtkScalarType, elementSizeBytes))
    {
      err = QStringLiteral("Unsupported dtype: ") + descr;
      return false;
    }

    qint64 voxels = 1;
    for (qint64 s : shape)
      voxels *= s;
    const qint64 expectedBytes = voxels * elementSizeBytes;
    if (dataOffset < 0 || dataOffset + expectedBytes > blob.size())
    {
      err = QStringLiteral("NPY data truncated");
      return false;
    }

    out.shape = shape;
    out.vtkScalarType = vtkScalarType;
    out.elementSizeBytes = elementSizeBytes;
    out.data = blob.mid(dataOffset, int(expectedBytes));

    if (!reduceTo3D(out, err))
      return false;

    return true;
  }

  void computeRobustWindowLevel(const NpyData &npy, double &window, double &level)
  {
    const qint64 voxels = qint64(npy.shape[0]) * qint64(npy.shape[1]) * qint64(npy.shape[2]);
    if (voxels <= 0 || npy.elementSizeBytes <= 0 || npy.data.size() < voxels * npy.elementSizeBytes)
    {
      window = 1.0;
      level = 0.0;
      return;
    }

    const qint64 maxSamples = 200000;
    const qint64 stride = qMax<qint64>(1, voxels / maxSamples);

    QVector<double> samples;
    samples.reserve(int(qMin(maxSamples, voxels)));

    auto readValue = [&](qint64 i) -> double
    {
      const char *p = npy.data.constData() + i * npy.elementSizeBytes;
      switch (npy.vtkScalarType)
      {
      case VTK_UNSIGNED_CHAR:
        return double(*reinterpret_cast<const unsigned char *>(p));
      case VTK_SIGNED_CHAR:
        return double(*reinterpret_cast<const signed char *>(p));
      case VTK_UNSIGNED_SHORT:
        return double(*reinterpret_cast<const unsigned short *>(p));
      case VTK_SHORT:
        return double(*reinterpret_cast<const short *>(p));
      case VTK_UNSIGNED_INT:
        return double(*reinterpret_cast<const unsigned int *>(p));
      case VTK_INT:
        return double(*reinterpret_cast<const int *>(p));
      case VTK_UNSIGNED_LONG_LONG:
        return double(*reinterpret_cast<const unsigned long long *>(p));
      case VTK_LONG_LONG:
        return double(*reinterpret_cast<const long long *>(p));
      case VTK_FLOAT:
        return double(*reinterpret_cast<const float *>(p));
      case VTK_DOUBLE:
        return *reinterpret_cast<const double *>(p);
      default:
        return 0.0;
      }
    };

    for (qint64 i = 0; i < voxels; i += stride)
      samples.push_back(readValue(i));
    if (samples.isEmpty())
    {
      window = 1.0;
      level = 0.0;
      return;
    }

    const int n = samples.size();
    const int loIdx = qBound(0, int(double(n - 1) * 0.005), n - 1);
    const int hiIdx = qBound(0, int(double(n - 1) * 0.995), n - 1);

    QVector<double> tmp = samples;
    std::nth_element(tmp.begin(), tmp.begin() + loIdx, tmp.end());
    const double lo = tmp[loIdx];
    std::nth_element(tmp.begin(), tmp.begin() + hiIdx, tmp.end());
    const double hi = tmp[hiIdx];

    window = hi - lo;
    level = (hi + lo) * 0.5;
    if (!(window > 0.0))
    {
      window = 1.0;
      level = lo;
    }
  }
}

Analyze3DWindow::Analyze3DWindow(QWidget *parent) : QMainWindow(parent)
{
  setWindowTitle(pick("3D 分析查看器", "3D Analysis Viewer"));
  resize(1000, 800);

  auto *central = new QWidget(this);
  setCentralWidget(central);

  auto *root = new QVBoxLayout();
  root->setContentsMargins(40, 24, 40, 24);
  root->setSpacing(12);
  central->setLayout(root);

  m_title = new QLabel(central);
  m_title->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.92);font-size:22px;font-weight:800;}");
  root->addWidget(m_title);

  auto *bar = new QFrame(central);
  bar->setStyleSheet(
      "QFrame{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:18px;}");
  AppConfig::installGlassCard(bar);
  auto *barL = new QHBoxLayout();
  barL->setContentsMargins(16, 14, 16, 14);
  barL->setSpacing(10);
  bar->setLayout(barL);

  m_loadBtn = new QPushButton(bar);
  m_loadBtn->setCursor(Qt::PointingHandCursor);
  m_loadBtn->setProperty("primary", true);
  connect(m_loadBtn, &QPushButton::clicked, this, &Analyze3DWindow::onLoadNpZ);
  barL->addWidget(m_loadBtn);

  m_fileLabel = new QLabel(bar);
  m_fileLabel->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:11px;}");
  m_fileLabel->setTextInteractionFlags(Qt::TextSelectableByMouse);
  barL->addWidget(m_fileLabel, 1);

  auto *vsep = new QFrame(bar);
  vsep->setFrameShape(QFrame::VLine);
  vsep->setStyleSheet("QFrame{color:rgba(255,255,255,0.16);}");
  barL->addWidget(vsep);

  m_modeLabel = new QLabel(bar);
  barL->addWidget(m_modeLabel);

  m_modeCombo = new QComboBox(bar);
  m_modeCombo->setFixedWidth(180);
  connect(m_modeCombo, &QComboBox::currentIndexChanged, this, &Analyze3DWindow::onKeyChanged);
  barL->addWidget(m_modeCombo);

  auto *vsep2 = new QFrame(bar);
  vsep2->setFrameShape(QFrame::VLine);
  vsep2->setStyleSheet("QFrame{color:rgba(255,255,255,0.16);}");
  barL->addWidget(vsep2);

  m_orientLabel = new QLabel(bar);
  barL->addWidget(m_orientLabel);

  auto *group = new QButtonGroup(this);
  m_front = new QRadioButton(bar);
  m_side = new QRadioButton(bar);
  m_top = new QRadioButton(bar);
  group->addButton(m_front);
  group->addButton(m_side);
  group->addButton(m_top);
  m_front->setChecked(true);
  connect(group, &QButtonGroup::buttonToggled, this,
          [this](QAbstractButton *, bool checked)
          {
            if (checked)
              onOrientationChanged();
          });
  barL->addWidget(m_front);
  barL->addWidget(m_side);
  barL->addWidget(m_top);

  barL->addStretch(1);

  m_hint = new QLabel(bar);
  m_hint->setStyleSheet(
      "QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);font-size:11px;}");
  barL->addWidget(m_hint);

  root->addWidget(bar);

  m_view = new QFrame(central);
  m_view->setStyleSheet(
      "QFrame{background:rgba(0,0,0,0.18);border:1px solid rgba(255,255,255,0.12);border-radius:18px;} QLabel{background:transparent;border:0px;color:rgba(255,255,255,0.62);}");
  AppConfig::installGlassCard(m_view);
  auto *viewL = new QVBoxLayout();
  viewL->setContentsMargins(14, 14, 14, 14);
  viewL->setSpacing(10);
  m_view->setLayout(viewL);

  auto *vtkWrap = new QFrame(m_view);
  vtkWrap->setStyleSheet(
      "QFrame{background:rgba(0,0,0,0.18);border:1px dashed rgba(255,255,255,0.16);border-radius:14px;}");
  auto *vtkL = new QVBoxLayout();
  vtkL->setContentsMargins(0, 0, 0, 0);
  vtkL->setSpacing(0);
  vtkWrap->setLayout(vtkL);

  m_vtkWidget = new QVTKOpenGLNativeWidget(vtkWrap);
  m_vtkWidget->setMinimumHeight(480);
  vtkL->addWidget(m_vtkWidget, 1);
  viewL->addWidget(vtkWrap, 1);

  m_renderWindow = vtkSmartPointer<vtkGenericOpenGLRenderWindow>::New();
  m_renderWindow->SetMultiSamples(0);
  m_vtkWidget->setRenderWindow(m_renderWindow);
  m_renderer = vtkSmartPointer<vtkRenderer>::New();
  m_renderer->SetBackground(0.1, 0.1, 0.1);
  m_renderWindow->AddRenderer(m_renderer);

  root->addWidget(m_view, 1);

  auto *sx = new QShortcut(QKeySequence(Qt::Key_X), this);
  sx->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sx, &QShortcut::activated, this, [this]()
          {
            if (m_side)
              m_side->setChecked(true); });

  auto *sy = new QShortcut(QKeySequence(Qt::Key_Y), this);
  sy->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sy, &QShortcut::activated, this, [this]()
          {
            if (m_top)
              m_top->setChecked(true); });

  auto *sz = new QShortcut(QKeySequence(Qt::Key_Z), this);
  sz->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sz, &QShortcut::activated, this, [this]()
          {
            if (m_front)
              m_front->setChecked(true); });

  auto *sr = new QShortcut(QKeySequence(Qt::Key_R), this);
  sr->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sr, &QShortcut::activated, this, [this]()
          { resetCamera(); });

  auto *sd = new QShortcut(QKeySequence(Qt::Key_D), this);
  sd->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sd, &QShortcut::activated, this, [this]()
          { resetWindowLevel(); });

  auto *sUp = new QShortcut(QKeySequence(Qt::Key_Up), this);
  sUp->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sUp, &QShortcut::activated, this, [this]()
          { stepSlice(-1); });

  auto *sDown = new QShortcut(QKeySequence(Qt::Key_Down), this);
  sDown->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sDown, &QShortcut::activated, this, [this]()
          { stepSlice(1); });

  auto *sPgUp = new QShortcut(QKeySequence(Qt::Key_PageUp), this);
  sPgUp->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sPgUp, &QShortcut::activated, this, [this]()
          { stepSlice(-10); });

  auto *sPgDown = new QShortcut(QKeySequence(Qt::Key_PageDown), this);
  sPgDown->setContext(Qt::WidgetWithChildrenShortcut);
  connect(sPgDown, &QShortcut::activated, this, [this]()
          { stepSlice(10); });

  setThemeColor(m_bg);
  setLanguage(m_lang);
}

void Analyze3DWindow::launchPythonGui(QWidget *parent, const QString &lang,
                                      const QString &suggestedNpzPath)
{
  const QString l = (lang == "EN") ? "EN" : "CN";
  const QString script = pythonAnalyzeGuiScript();
  if (script.isEmpty())
  {
    AppConfig::showToast(parent, (l == "EN") ? "Error" : "错误",
                         (l == "EN") ? "3D visualization script not found."
                                     : "未找到 Python 版 3D 可视化脚本。",
                         4200);
    return;
  }

  QStringList args;
  args << script;

  const QString npz = QDir::cleanPath(suggestedNpzPath.trimmed());
  if (!npz.isEmpty() && npz.toLower().endsWith(".npz") && QFileInfo::exists(npz))
    args << npz;

  const bool ok = QProcess::startDetached(AppConfig::pythonExecutablePath(), args, repoRootDir());
  if (!ok)
  {
    AppConfig::showToast(parent, (l == "EN") ? "Error" : "错误",
                         (l == "EN") ? "Failed to launch 3D visualization."
                                     : "启动 3D 可视化失败。",
                         4200);
    return;
  }

  AppConfig::showToast(parent, (l == "EN") ? "Info" : "提示",
                       (l == "EN") ? "3D visualization opened."
                                   : "已打开 3D 可视化。",
                       2000);
}

void Analyze3DWindow::setThemeColor(const QColor &bg)
{
  m_bg = bg;
  setAutoFillBackground(false);
  if (centralWidget())
    centralWidget()->setAutoFillBackground(false);
}

void Analyze3DWindow::setLanguage(const QString &lang)
{
  m_lang = (lang == "EN") ? "EN" : "CN";
  applyLanguage();
}

void Analyze3DWindow::openNpzFile(const QString &path)
{
  const QString f = QDir::cleanPath(path.trimmed());
  if (f.isEmpty() || !f.toLower().endsWith(".npz") || !QFileInfo::exists(f))
    return;
  m_npzPath = f;
  if (m_fileLabel)
    m_fileLabel->setText(f);
  loadKeysFromNpz(f);
  if (!m_keys.isEmpty() && m_modeCombo)
  {
    m_modeCombo->setCurrentIndex(0);
    updateVisualization();
  }
}

void Analyze3DWindow::onLoadNpZ()
{
  const QString f = QFileDialog::getOpenFileName(
      this, pick("选择 NPZ 文件", "Select NPZ File"), QString(),
      pick("Numpy 文件 (*.npz);;所有文件 (*.*)", "Numpy files (*.npz);;All files (*.*)"));
  if (f.isEmpty())
    return;
  openNpzFile(f);
}

QString Analyze3DWindow::pick(const QString &cn, const QString &en) const
{
  return (m_lang == "EN") ? en : cn;
}

void Analyze3DWindow::applyLanguage()
{
  setWindowTitle(pick("3D 分析查看器", "3D Analysis Viewer"));
  if (m_title)
    m_title->setText(pick("3D 分析查看器", "3D Analysis Viewer"));
  if (m_loadBtn)
    m_loadBtn->setText(pick("载入 NPZ", "Load NPZ"));
  if (m_fileLabel && m_fileLabel->text().isEmpty())
  {
    m_fileLabel->setText(pick("未选择文件", "No file selected"));
  }
  if (m_modeLabel)
    m_modeLabel->setText(pick("当前模式:", "Current key:"));
  if (m_orientLabel)
    m_orientLabel->setText(pick("视图:", "View:"));
  if (m_front)
    m_front->setText(pick("轴状位(Z)", "Axial (Z)"));
  if (m_side)
    m_side->setText(pick("矢状位(X)", "Sagittal (X)"));
  if (m_top)
    m_top->setText(pick("冠状位(Y)", "Coronal (Y)"));
  if (m_hint)
    m_hint->setText(pick("左键拖动：移动切片 / 旋转（边缘）。中键：调整窗宽窗位。",
                         "Left drag: move slice / rotate (edge). Middle: window/level."));
}

QString Analyze3DWindow::currentAxis() const
{
  if (m_side && m_side->isChecked())
    return QStringLiteral("X");
  if (m_top && m_top->isChecked())
    return QStringLiteral("Y");
  return QStringLiteral("Z");
}

void Analyze3DWindow::loadKeysFromNpz(const QString &npzPath)
{
  QString err;
  const QStringList keys = listNpzKeys(npzPath, err);
  m_keys = keys;

  if (m_modeCombo)
  {
    m_modeCombo->blockSignals(true);
    m_modeCombo->clear();
    for (const QString &k : keys)
      m_modeCombo->addItem(k, k);
    m_modeCombo->blockSignals(false);
  }

  if (keys.isEmpty())
  {
    AppConfig::showToast(this, pick("错误", "Error"),
                         err.isEmpty() ? pick("未找到 NPZ 数据键。", "No NPZ keys found.")
                                       : err,
                         4200);
  }
}

void Analyze3DWindow::updateVisualization()
{
  if (m_npzPath.trimmed().isEmpty() || !QFileInfo::exists(m_npzPath))
    return;

  const QString key = m_modeCombo ? m_modeCombo->currentData().toString().trimmed() : QString();
  if (key.isEmpty())
    return;

  NpyData npy;
  QString err;
  if (!loadNpzEntryAsNpy(m_npzPath, key, npy, err))
  {
    AppConfig::showToast(this, pick("错误", "Error"),
                         pick("加载数据失败：", "Failed to load data: ") + err, 4200);
    return;
  }

  if (npy.shape.size() != 3)
  {
    AppConfig::showToast(this, pick("错误", "Error"),
                         pick("当前数据不是 3D 体数据。", "Selected data is not a 3D volume."),
                         4200);
    return;
  }

  const int d = int(npy.shape[0]);
  const int h = int(npy.shape[1]);
  const int w = int(npy.shape[2]);
  if (d <= 0 || h <= 0 || w <= 0)
    return;

  m_volumeBytes = npy.data;
  computeRobustWindowLevel(npy, m_defaultWindow, m_defaultLevel);

  if (!m_importer)
    m_importer = vtkSmartPointer<vtkImageImport>::New();
  m_importer->SetNumberOfScalarComponents(1);
  m_importer->SetDataScalarType(npy.vtkScalarType);
  m_importer->SetWholeExtent(0, w - 1, 0, h - 1, 0, d - 1);
  m_importer->SetDataExtentToWholeExtent();
  m_importer->SetImportVoidPointer(m_volumeBytes.data(), 1);
  m_importer->Update();

  if (!m_cast)
    m_cast = vtkSmartPointer<vtkImageCast>::New();
  m_cast->SetInputConnection(m_importer->GetOutputPort());
  m_cast->SetOutputScalarTypeToFloat();
  m_cast->ClampOverflowOn();
  m_cast->Update();

  m_imageData = m_cast->GetOutput();
  if (!m_renderer)
    return;

  if (m_planeWidget)
  {
    m_planeWidget->Off();
    m_planeWidget->SetInteractor(nullptr);
    m_planeWidget = nullptr;
  }

  m_renderer->RemoveAllViewProps();

  auto outline = vtkSmartPointer<vtkOutlineFilter>::New();
  outline->SetInputData(m_imageData);
  auto outlineMapper = vtkSmartPointer<vtkPolyDataMapper>::New();
  outlineMapper->SetInputConnection(outline->GetOutputPort());
  auto outlineActor = vtkSmartPointer<vtkActor>::New();
  outlineActor->SetMapper(outlineMapper);
  m_renderer->AddActor(outlineActor);

  vtkRenderWindowInteractor *iren = nullptr;
  if (m_vtkWidget)
    iren = m_vtkWidget->interactor();
  if (!iren && m_renderWindow)
    iren = m_renderWindow->GetInteractor();
  if (iren)
  {
    iren->SetInteractorStyle(vtkSmartPointer<vtkInteractorStyleTrackballCamera>::New());
    iren->SetDesiredUpdateRate(30.0);
    iren->SetStillUpdateRate(0.2);
  }

  m_planeWidget = vtkSmartPointer<vtkImagePlaneWidget>::New();
  m_planeWidget->SetInputData(m_imageData);
  m_planeWidget->SetDefaultRenderer(m_renderer);
  if (iren)
    m_planeWidget->SetInteractor(iren);

  m_planeWidget->SetMarginSizeX(0.08);
  m_planeWidget->SetMarginSizeY(0.08);
  m_planeWidget->TextureInterpolateOn();
  m_planeWidget->SetResliceInterpolateToLinear();
  m_planeWidget->UseContinuousCursorOn();
  if (auto *tp = m_planeWidget->GetTextProperty())
  {
    tp->SetColor(1.0, 1.0, 1.0);
    tp->SetFontSize(14);
  }

  m_planeWidget->SetLeftButtonAction(vtkImagePlaneWidget::VTK_SLICE_MOTION_ACTION);
  m_planeWidget->SetMiddleButtonAction(vtkImagePlaneWidget::VTK_WINDOW_LEVEL_ACTION);
  m_planeWidget->SetRightButtonAction(vtkImagePlaneWidget::VTK_CURSOR_ACTION);
  if (m_defaultWindow > 0.0)
    m_planeWidget->SetWindowLevel(m_defaultWindow, m_defaultLevel, 1);
  m_planeWidget->DisplayTextOn();

  if (!m_onStartInteraction)
  {
    m_onStartInteraction = vtkSmartPointer<vtkCallbackCommand>::New();
    m_onStartInteraction->SetClientData(this);
    m_onStartInteraction->SetCallback(&Analyze3DWindow::onPlaneStartInteraction);
  }
  if (!m_onEndInteraction)
  {
    m_onEndInteraction = vtkSmartPointer<vtkCallbackCommand>::New();
    m_onEndInteraction->SetClientData(this);
    m_onEndInteraction->SetCallback(&Analyze3DWindow::onPlaneEndInteraction);
  }
  m_planeWidget->AddObserver(vtkCommand::StartInteractionEvent, m_onStartInteraction);
  m_planeWidget->AddObserver(vtkCommand::EndInteractionEvent, m_onEndInteraction);

  m_planeWidget->On();

  setOrientationAxis(currentAxis());

  m_renderer->ResetCamera();
  if (m_renderWindow)
    m_renderWindow->Render();
}

void Analyze3DWindow::onPlaneStartInteraction(vtkObject *, unsigned long, void *clientData, void *)
{
  auto *self = static_cast<Analyze3DWindow *>(clientData);
  if (!self || !self->m_planeWidget)
    return;
  self->m_planeWidget->DisplayTextOff();
  self->m_planeWidget->TextureInterpolateOff();
  self->m_planeWidget->SetResliceInterpolateToNearestNeighbour();
}

void Analyze3DWindow::onPlaneEndInteraction(vtkObject *, unsigned long, void *clientData, void *)
{
  auto *self = static_cast<Analyze3DWindow *>(clientData);
  if (!self || !self->m_planeWidget)
    return;
  self->m_planeWidget->TextureInterpolateOn();
  self->m_planeWidget->SetResliceInterpolateToLinear();
  self->m_planeWidget->DisplayTextOn();
  if (self->m_defaultWindow > 0.0)
    self->m_planeWidget->SetWindowLevel(self->m_defaultWindow, self->m_defaultLevel, 1);
  if (self->m_renderWindow)
    self->m_renderWindow->Render();
}

void Analyze3DWindow::stepSlice(int delta)
{
  if (!m_planeWidget || !m_imageData)
    return;
  int dims[3] = {0, 0, 0};
  m_imageData->GetDimensions(dims);
  const QString axis = currentAxis();
  const int maxIdx = (axis == QStringLiteral("X"))
                         ? dims[0] - 1
                     : (axis == QStringLiteral("Y"))
                         ? dims[1] - 1
                         : dims[2] - 1;
  if (maxIdx <= 0)
    return;
  const int cur = m_planeWidget->GetSliceIndex();
  const int next = qBound(0, cur + delta, maxIdx);
  if (next == cur)
    return;
  m_planeWidget->SetSliceIndex(next);
  if (m_renderWindow)
    m_renderWindow->Render();
}

void Analyze3DWindow::resetCamera()
{
  if (!m_renderer)
    return;
  m_renderer->ResetCamera();
  if (m_renderWindow)
    m_renderWindow->Render();
}

void Analyze3DWindow::resetWindowLevel()
{
  if (!m_planeWidget)
    return;
  if (m_defaultWindow > 0.0)
    m_planeWidget->SetWindowLevel(m_defaultWindow, m_defaultLevel, 1);
  if (m_renderWindow)
    m_renderWindow->Render();
}

void Analyze3DWindow::setOrientationAxis(const QString &axis)
{
  if (!m_planeWidget || !m_imageData)
    return;
  int dims[3] = {0, 0, 0};
  m_imageData->GetDimensions(dims);
  if (dims[0] <= 0 || dims[1] <= 0 || dims[2] <= 0)
    return;

  if (axis == QStringLiteral("X"))
  {
    m_planeWidget->SetPlaneOrientationToXAxes();
    m_planeWidget->SetSliceIndex(dims[0] / 2);
  }
  else if (axis == QStringLiteral("Y"))
  {
    m_planeWidget->SetPlaneOrientationToYAxes();
    m_planeWidget->SetSliceIndex(dims[1] / 2);
  }
  else
  {
    m_planeWidget->SetPlaneOrientationToZAxes();
    m_planeWidget->SetSliceIndex(dims[2] / 2);
  }

  if (m_renderWindow)
    m_renderWindow->Render();
}

void Analyze3DWindow::onKeyChanged(int)
{
  updateVisualization();
}

void Analyze3DWindow::onOrientationChanged()
{
  setOrientationAxis(currentAxis());
}
