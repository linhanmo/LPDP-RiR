#include "AppConfig.h"

#include <QAbstractAnimation>
#include <QApplication>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QGraphicsOpacityEffect>
#include <QLabel>
#include <QGraphicsDropShadowEffect>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPainter>
#include <QPainterPath>
#include <QProcess>
#include <QProcessEnvironment>
#include <QPropertyAnimation>
#include <QRandomGenerator>
#include <QScreen>
#include <QThread>
#include <QPushButton>
#include <QSqlDatabase>
#include <QSqlError>
#include <QSqlQuery>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>

#include "MagneticButtonStage.h"

#ifdef Q_OS_WIN
#include <windows.h>
#endif

namespace
{
  QJsonObject defaultConfig()
  {
    QJsonObject o;
    o.insert("language", "CN");
    o.insert("theme_index", 1);
    o.insert("remember_me", false);
    o.insert("perf_threads", 0);
    o.insert("perf_interop_threads", 0);
    o.insert("perf_workers", 0);
    o.insert("perf_priority", "normal");
    return o;
  }

  QJsonObject loadConfig(const QString &path)
  {
    QFile f(path);
    if (!f.exists())
      return defaultConfig();
    if (!f.open(QIODevice::ReadOnly))
      return defaultConfig();
    const QByteArray raw = f.readAll();
    f.close();
    const auto doc = QJsonDocument::fromJson(raw);
    if (!doc.isObject())
      return defaultConfig();
    QJsonObject o = doc.object();
    if (!o.contains("language"))
      o.insert("language", "CN");
    if (!o.contains("theme_index"))
      o.insert("theme_index", 1);
    if (!o.contains("remember_me"))
      o.insert("remember_me", false);
    if (!o.contains("perf_threads"))
      o.insert("perf_threads", 0);
    if (!o.contains("perf_interop_threads"))
      o.insert("perf_interop_threads", 0);
    if (!o.contains("perf_workers"))
      o.insert("perf_workers", 0);
    if (!o.contains("perf_priority"))
      o.insert("perf_priority", "normal");
    return o;
  }

  void saveConfig(const QString &path, const QJsonObject &o)
  {
    QFile f(path);
    QDir().mkpath(QFileInfo(path).absolutePath());
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate))
      return;
    f.write(QJsonDocument(o).toJson(QJsonDocument::Indented));
    f.close();
  }

  QString findRepoFile(const QString &relativePath)
  {
    QDir dir(QCoreApplication::applicationDirPath());
    for (int i = 0; i < 10; ++i)
    {
      const QString candidate = dir.filePath(relativePath);
      if (QFile::exists(candidate) || QFileInfo(candidate).absoluteDir().exists())
      {
        return candidate;
      }
      if (!dir.cdUp())
        break;
    }
    return QString();
  }

  QSqlDatabase ensureDbOpen()
  {
    const QString connName = "lpdp_rir";
    QSqlDatabase db;
    if (QSqlDatabase::contains(connName))
    {
      db = QSqlDatabase::database(connName);
    }
    else
    {
      db = QSqlDatabase::addDatabase("QSQLITE", connName);
      db.setDatabaseName(AppConfig::databaseFilePath());
    }
    if (!db.isOpen())
    {
      db.open();
    }
    return db;
  }

  void initDb()
  {
    QSqlDatabase db = ensureDbOpen();
    if (!db.isOpen())
      return;
    QSqlQuery q(db);
    q.exec("PRAGMA foreign_keys=ON");
    q.exec("CREATE TABLE IF NOT EXISTS users ("
           "username TEXT PRIMARY KEY,"
           "password TEXT,"
           "registration_time TEXT,"
           "last_log_in_time TEXT"
           ")");
    q.exec("CREATE TABLE IF NOT EXISTS datastorage ("
           "id INTEGER PRIMARY KEY AUTOINCREMENT,"
           "username TEXT,"
           "foldername TEXT,"
           "FOREIGN KEY(username) REFERENCES users(username)"
           ")");
  }

  bool constantTimeEqual(const QByteArray &a, const QByteArray &b)
  {
    if (a.size() != b.size())
      return false;
    unsigned char diff = 0;
    for (int i = 0; i < a.size(); ++i)
    {
      diff |= static_cast<unsigned char>(a.at(i)) ^ static_cast<unsigned char>(b.at(i));
    }
    return diff == 0;
  }

  QByteArray hmacSha256(const QByteArray &key, const QByteArray &message)
  {
    QByteArray k = key;
    constexpr int blockSize = 64;
    if (k.size() > blockSize)
    {
      k = QCryptographicHash::hash(k, QCryptographicHash::Sha256);
    }
    if (k.size() < blockSize)
    {
      k.append(QByteArray(blockSize - k.size(), '\0'));
    }

    QByteArray oKeyPad(blockSize, '\0');
    QByteArray iKeyPad(blockSize, '\0');
    for (int i = 0; i < blockSize; ++i)
    {
      const unsigned char kb = static_cast<unsigned char>(k.at(i));
      oKeyPad[i] = static_cast<char>(kb ^ 0x5c);
      iKeyPad[i] = static_cast<char>(kb ^ 0x36);
    }

    const QByteArray inner = QCryptographicHash::hash(iKeyPad + message, QCryptographicHash::Sha256);
    return QCryptographicHash::hash(oKeyPad + inner, QCryptographicHash::Sha256);
  }

  QByteArray pbkdf2HmacSha256(const QByteArray &password, const QByteArray &salt, int iterations,
                              int dkLen)
  {
    if (iterations <= 0 || dkLen <= 0)
      return QByteArray();
    constexpr int hLen = 32;
    const int l = (dkLen + hLen - 1) / hLen;
    QByteArray out;
    out.reserve(l * hLen);

    for (int blockIndex = 1; blockIndex <= l; ++blockIndex)
    {
      QByteArray intBe(4, '\0');
      intBe[0] = static_cast<char>((blockIndex >> 24) & 0xFF);
      intBe[1] = static_cast<char>((blockIndex >> 16) & 0xFF);
      intBe[2] = static_cast<char>((blockIndex >> 8) & 0xFF);
      intBe[3] = static_cast<char>(blockIndex & 0xFF);

      QByteArray u = hmacSha256(password, salt + intBe);
      QByteArray t = u;
      for (int i = 1; i < iterations; ++i)
      {
        u = hmacSha256(password, u);
        for (int j = 0; j < hLen; ++j)
        {
          t[j] = static_cast<char>(static_cast<unsigned char>(t.at(j)) ^
                                   static_cast<unsigned char>(u.at(j)));
        }
      }
      out.append(t);
    }

    out.truncate(dkLen);
    return out;
  }

  QString makeStoredPassword(const QString &password, int iterations = 200000)
  {
    QByteArray salt(16, Qt::Uninitialized);
    for (int i = 0; i < salt.size(); ++i)
    {
      salt[i] = static_cast<char>(QRandomGenerator::global()->generate() & 0xFF);
    }
    const QByteArray key = pbkdf2HmacSha256(password.toUtf8(), salt, iterations, 32);
    const QString hashHex = QString::fromLatin1(key.toHex());
    const QString saltHex = QString::fromLatin1(salt.toHex());
    return QString("%1$%2$%3").arg(hashHex, saltHex, QString::number(iterations));
  }

  bool verifyStoredPassword(const QString &password, const QString &stored)
  {
    const QStringList parts = stored.split('$');
    if (parts.size() != 3)
      return false;
    const QByteArray storedHash = QByteArray::fromHex(parts.at(0).toLatin1());
    const QByteArray salt = QByteArray::fromHex(parts.at(1).toLatin1());
    bool ok = false;
    const int iters = parts.at(2).toInt(&ok);
    if (!ok || iters <= 0)
      return false;
    const QByteArray key = pbkdf2HmacSha256(password.toUtf8(), salt, iters, storedHash.size());
    return constantTimeEqual(key, storedHash);
  }

  QVector<QColor> themeColors()
  {
    return {
        QColor("#0B1220"),
        QColor("#0B1220"),
        QColor("#0B1220"),
        QColor("#0B1220"),
        QColor("#0B1220"),
        QColor("#0B1220"),
    };
  }

  int clampInt(int v, int lo, int hi)
  {
    if (v < lo)
      return lo;
    if (v > hi)
      return hi;
    return v;
  }

#ifdef Q_OS_WIN
  DWORD priorityClassFromString(const QString &s)
  {
    const QString k = s.trimmed().toLower();
    if (k == "idle")
      return IDLE_PRIORITY_CLASS;
    if (k == "below_normal" || k == "belownormal")
      return BELOW_NORMAL_PRIORITY_CLASS;
    if (k == "above_normal" || k == "abovenormal")
      return ABOVE_NORMAL_PRIORITY_CLASS;
    if (k == "high")
      return HIGH_PRIORITY_CLASS;
    return NORMAL_PRIORITY_CLASS;
  }
#endif
}

QString AppConfig::configFilePath()
{
  const QString p = findRepoFile("application_cpp/data/config.json");
  if (!p.isEmpty())
    return p;
  QDir dir(QCoreApplication::applicationDirPath());
  return dir.filePath("config.json");
}

QString AppConfig::databaseFilePath()
{
  const QString p = findRepoFile("application_cpp/data/data.db");
  if (!p.isEmpty())
    return p;
  QDir dir(QCoreApplication::applicationDirPath());
  return dir.filePath("data.db");
}

QString AppConfig::sessionFilePath()
{
  const QString p = findRepoFile("application_cpp/data/.session_user");
  if (!p.isEmpty())
    return p;
  QDir dir(QCoreApplication::applicationDirPath());
  return dir.filePath(".session_user");
}

QString AppConfig::pythonExecutablePath()
{
  const QString p = findRepoFile("env/python.exe");
  if (!p.isEmpty() && QFileInfo::exists(p))
    return p;
  return QStringLiteral("python");
}

QString AppConfig::language()
{
  const auto cfg = loadConfig(configFilePath());
  const QString lang = cfg.value("language").toString("CN");
  return (lang == "EN") ? "EN" : "CN";
}

void AppConfig::setLanguage(const QString &lang)
{
  QJsonObject cfg = loadConfig(configFilePath());
  cfg.insert("language", (lang == "EN") ? "EN" : "CN");
  saveConfig(configFilePath(), cfg);
}

int AppConfig::performanceThreads()
{
  const auto cfg = loadConfig(configFilePath());
  const int configured = cfg.value("perf_threads").toInt(0);
  const int ideal = qMax(1, QThread::idealThreadCount());
  return clampInt(configured > 0 ? configured : ideal, 1, 256);
}

int AppConfig::performanceInteropThreads()
{
  const auto cfg = loadConfig(configFilePath());
  const int configured = cfg.value("perf_interop_threads").toInt(0);
  const int threads = performanceThreads();
  const int fallback = qMax(1, threads / 2);
  return clampInt(configured > 0 ? configured : fallback, 1, 256);
}

int AppConfig::performanceWorkers()
{
  const auto cfg = loadConfig(configFilePath());
  const int configured = cfg.value("perf_workers").toInt(0);
  const int threads = performanceThreads();
  const int fallback = qMax(1, qMin(8, threads));
  return clampInt(configured > 0 ? configured : fallback, 1, 64);
}

QString AppConfig::performancePriority()
{
  const auto cfg = loadConfig(configFilePath());
  const QString p = cfg.value("perf_priority").toString("normal").trimmed();
  return p.isEmpty() ? QStringLiteral("normal") : p;
}

QProcessEnvironment AppConfig::pythonProcessEnvironment()
{
  QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
  const int threads = performanceThreads();
  const int interop = performanceInteropThreads();

  const QString t = QString::number(threads);
  const QString ti = QString::number(interop);
  env.insert(QStringLiteral("OMP_NUM_THREADS"), t);
  env.insert(QStringLiteral("MKL_NUM_THREADS"), t);
  env.insert(QStringLiteral("OPENBLAS_NUM_THREADS"), t);
  env.insert(QStringLiteral("NUMEXPR_NUM_THREADS"), t);
  env.insert(QStringLiteral("VECLIB_MAXIMUM_THREADS"), t);
  env.insert(QStringLiteral("BLIS_NUM_THREADS"), t);
  env.insert(QStringLiteral("TF_NUM_INTRAOP_THREADS"), t);
  env.insert(QStringLiteral("TF_NUM_INTEROP_THREADS"), ti);

  env.insert(QStringLiteral("PYTHONUNBUFFERED"), QStringLiteral("1"));
  return env;
}

void AppConfig::configurePythonProcess(QProcess *proc)
{
  if (!proc)
    return;
  proc->setProcessEnvironment(pythonProcessEnvironment());

  QObject::connect(proc, &QProcess::started, proc, [proc]()
                   {
#ifdef Q_OS_WIN
    const qint64 pid64 = proc->processId();
    if (pid64 <= 0)
      return;
    const DWORD pid = static_cast<DWORD>(pid64);
    HANDLE h = OpenProcess(PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION, FALSE, pid);
    if (!h)
      return;
    const DWORD cls = priorityClassFromString(AppConfig::performancePriority());
    SetPriorityClass(h, cls);
    CloseHandle(h);
#else
    Q_UNUSED(proc);
#endif
                   });
}

int AppConfig::themeIndex()
{
  const auto cfg = loadConfig(configFilePath());
  const int idx = cfg.value("theme_index").toInt(1);
  return idx;
}

void AppConfig::setThemeIndex(int index)
{
  QJsonObject cfg = loadConfig(configFilePath());
  cfg.insert("theme_index", index);
  saveConfig(configFilePath(), cfg);
}

QColor AppConfig::themeColor(int index)
{
  const auto list = themeColors();
  if (index >= 0 && index < list.size())
    return list[index];
  return QColor("#0B1220");
}

QVector<QColor> AppConfig::themeColorList() { return themeColors(); }

AppCredentials AppConfig::credentials()
{
  const auto cfg = loadConfig(configFilePath());
  AppCredentials c;
  c.rememberMe = cfg.value("remember_me").toBool(false);
  if (c.rememberMe)
  {
    c.username = cfg.value("saved_username").toString();
    c.password = cfg.value("saved_password").toString();
  }
  return c;
}

void AppConfig::saveCredentials(const QString &username, const QString &password,
                                bool rememberMe)
{
  QJsonObject cfg = loadConfig(configFilePath());
  cfg.insert("remember_me", rememberMe);
  cfg.insert("last_username", username);
  if (rememberMe)
  {
    cfg.insert("saved_username", username);
    cfg.insert("saved_password", password);
  }
  else
  {
    cfg.remove("saved_username");
    cfg.remove("saved_password");
  }
  saveConfig(configFilePath(), cfg);
}

bool AppConfig::createUser(const QString &username, const QString &password)
{
  const QString u = username.trimmed();
  if (u.isEmpty() || password.isEmpty())
    return false;
  initDb();
  QSqlDatabase db = ensureDbOpen();
  if (!db.isOpen())
    return false;

  {
    QSqlQuery q(db);
    q.prepare("SELECT username FROM users WHERE username=?");
    q.addBindValue(u);
    if (q.exec() && q.next())
      return false;
  }

  const QString storedPwd = makeStoredPassword(password);
  const QString now = QDateTime::currentDateTime().toString(Qt::ISODate);

  QSqlQuery q(db);
  q.prepare(
      "INSERT INTO users(username, password, registration_time, last_log_in_time) VALUES(?,?,?,?)");
  q.addBindValue(u);
  q.addBindValue(storedPwd);
  q.addBindValue(now);
  q.addBindValue(QVariant());
  return q.exec();
}

bool AppConfig::authenticateUser(const QString &username, const QString &password)
{
  const QString u = username.trimmed();
  if (u.isEmpty() || password.isEmpty())
    return false;
  initDb();
  QSqlDatabase db = ensureDbOpen();
  if (!db.isOpen())
    return false;

  QString storedPwd;
  {
    QSqlQuery q(db);
    q.prepare("SELECT password FROM users WHERE username=?");
    q.addBindValue(u);
    if (!q.exec() || !q.next())
      return false;
    storedPwd = q.value(0).toString();
  }

  if (!verifyStoredPassword(password, storedPwd))
    return false;

  {
    QSqlQuery q(db);
    q.prepare("UPDATE users SET last_log_in_time=? WHERE username=?");
    q.addBindValue(QDateTime::currentDateTime().toString(Qt::ISODate));
    q.addBindValue(u);
    q.exec();
  }

  setCurrentUser(u);
  return true;
}

bool AppConfig::changePassword(const QString &username, const QString &oldPassword,
                               const QString &newPassword)
{
  const QString u = username.trimmed();
  if (u.isEmpty() || oldPassword.isEmpty() || newPassword.isEmpty())
    return false;
  initDb();
  QSqlDatabase db = ensureDbOpen();
  if (!db.isOpen())
    return false;

  QString storedPwd;
  {
    QSqlQuery q(db);
    q.prepare("SELECT password FROM users WHERE username=?");
    q.addBindValue(u);
    if (!q.exec() || !q.next())
      return false;
    storedPwd = q.value(0).toString();
  }

  if (!verifyStoredPassword(oldPassword, storedPwd))
    return false;

  const QString newStored = makeStoredPassword(newPassword);
  QSqlQuery q(db);
  q.prepare("UPDATE users SET password=? WHERE username=?");
  q.addBindValue(newStored);
  q.addBindValue(u);
  return q.exec();
}

QString AppConfig::currentUser()
{
  QString u;
  QFile f(sessionFilePath());
  if (f.exists() && f.open(QIODevice::ReadOnly))
  {
    u = QString::fromUtf8(f.readAll()).trimmed();
    f.close();
  }
  if (!u.isEmpty())
    return u;

  const auto cfg = loadConfig(configFilePath());
  const QString last = cfg.value("last_username").toString().trimmed();
  if (!last.isEmpty())
    return last;
  return cfg.value("saved_username").toString().trimmed();
}

void AppConfig::setCurrentUser(const QString &username)
{
  QFile f(sessionFilePath());
  QDir().mkpath(QFileInfo(sessionFilePath()).absolutePath());
  if (f.open(QIODevice::WriteOnly | QIODevice::Truncate))
  {
    f.write(username.toUtf8());
    f.close();
  }

  QJsonObject cfg = loadConfig(configFilePath());
  cfg.insert("last_username", username);
  saveConfig(configFilePath(), cfg);
}

QVector<QString> AppConfig::userHistoryFolders(const QString &username)
{
  const QString u = username.trimmed();
  if (u.isEmpty())
    return {};
  initDb();
  QSqlDatabase db = ensureDbOpen();
  if (!db.isOpen())
    return {};

  QSqlQuery q(db);
  q.prepare("SELECT foldername FROM datastorage WHERE username=? ORDER BY id DESC");
  q.addBindValue(u);
  if (!q.exec())
    return {};

  QVector<QString> out;
  while (q.next())
  {
    const QString folder = q.value(0).toString();
    if (!folder.isEmpty())
      out.push_back(folder);
  }
  return out;
}

int AppConfig::cleanupInvalidRecords()
{
  initDb();
  QSqlDatabase db = ensureDbOpen();
  if (!db.isOpen())
    return 0;

  QDir dataDir(QFileInfo(databaseFilePath()).absolutePath());
  if (!dataDir.cdUp())
    return 0;
  const QDir inputDir(dataDir.filePath("input"));
  if (!inputDir.exists())
    return 0;

  QSqlQuery q(db);
  if (!q.exec("SELECT id, foldername FROM datastorage"))
    return 0;

  QVector<int> toDelete;
  while (q.next())
  {
    const int id = q.value(0).toInt();
    const QString folderName = q.value(1).toString();
    if (folderName.isEmpty())
      continue;
    if (!QFileInfo::exists(inputDir.filePath(folderName)))
    {
      toDelete.push_back(id);
    }
  }

  if (toDelete.isEmpty())
    return 0;

  db.transaction();

  int deleted = 0;
  QSqlQuery del(db);
  del.prepare("DELETE FROM datastorage WHERE id=?");
  for (const int id : toDelete)
  {
    del.bindValue(0, id);
    if (del.exec())
      ++deleted;
    del.finish();
  }

  if (deleted > 0)
    db.commit();
  else
    db.rollback();

  return deleted;
}

QColor AppConfig::effectsBg() { return QColor("#0B1220"); }

QColor AppConfig::effectsCard() { return QColor(255, 255, 255, 15); }

QColor AppConfig::effectsCard2() { return QColor(255, 255, 255, 20); }

QColor AppConfig::effectsBorder() { return QColor(255, 255, 255, 31); }

QColor AppConfig::effectsText() { return QColor(255, 255, 255, 235); }

QColor AppConfig::effectsMuted() { return QColor(255, 255, 255, 166); }

QColor AppConfig::effectsAccent2()
{
  const int idx = themeIndex();
  if (idx == 0)
    return QColor("#67D1FF");
  if (idx == 1)
    return QColor("#9B7BFF");
  if (idx == 2)
    return QColor("#50FFC4");
  if (idx == 3)
    return QColor("#FF54C8");
  if (idx == 4)
    return QColor("#9B7BFF");
  return QColor("#9B7BFF");
}

QColor AppConfig::effectsAccent()
{
  const int idx = themeIndex();
  if (idx == 0)
    return QColor("#67D1FF");
  if (idx == 1)
    return QColor("#9B7BFF");
  if (idx == 2)
    return QColor("#50FFC4");
  if (idx == 3)
    return QColor("#FF54C8");
  if (idx == 4)
    return QColor("#67D1FF");
  return QColor("#67D1FF");
}

static QString rgbaCss(const QColor &c)
{
  return QString("rgba(%1,%2,%3,%4)")
      .arg(c.red())
      .arg(c.green())
      .arg(c.blue())
      .arg(QString::number(c.alphaF(), 'f', 3));
}

QString AppConfig::effectsGlobalStyleSheet()
{
  const QString bg = effectsBg().name(QColor::HexRgb);
  const QString card = rgbaCss(effectsCard());
  const QString card2 = rgbaCss(effectsCard2());
  const QString border = rgbaCss(effectsBorder());
  const QString text = rgbaCss(effectsText());
  const QString muted = rgbaCss(effectsMuted());
  const QString accent = effectsAccent().name(QColor::HexRgb);

  return QString(
             "QWidget{color:%1;}"
             "QScrollArea{background:transparent;border:0px;}"
             "QScrollArea QWidget#qt_scrollarea_viewport{background:transparent;}"
             "QLabel{color:%1;background:transparent;border:0px;}"
             "QLineEdit,QTextEdit,QPlainTextEdit{background:transparent;border:1px solid %3;border-radius:12px;padding:10px 12px;selection-background-color:rgba(103,209,255,0.35);selection-color:%4;}"
             "QLineEdit:read-only,QTextEdit:read-only,QPlainTextEdit:read-only{background:transparent;border:0px;padding:0px 2px;}"
             "QComboBox{background:transparent;border:1px solid %3;border-radius:12px;padding:10px 12px;}"
             "QComboBox::drop-down{border:0px;}"
             "QComboBox QAbstractItemView{background:#0C1426;color:%1;border:1px solid %3;selection-background-color:rgba(103,209,255,0.14);outline:0px;}"
             "QPushButton{border:1px solid rgba(255,255,255,0.16);background:rgba(255,255,255,0.08);color:%1;padding:10px 14px;border-radius:12px;font-weight:700;letter-spacing:0.2px;}"
             "QPushButton:hover{background:%5;border-color:rgba(255,255,255,0.20);}"
             "QPushButton:pressed{background:%2;}"
             "QPushButton[primary=\"true\"]{border-color:rgba(103,209,255,0.35);background:rgba(103,209,255,0.14);}"
             "QPushButton[primary=\"true\"]:hover{background:rgba(103,209,255,0.18);}"
             "QToolButton{border:1px solid rgba(255,255,255,0.16);background:rgba(255,255,255,0.08);color:%1;padding:8px 12px;border-radius:12px;font-weight:700;}"
             "QToolButton:hover{background:%5;}"
             "QMenu{background:rgba(0,0,0,0.55);border:1px solid rgba(255,255,255,0.14);border-radius:12px;padding:6px;}"
             "QMenu::item{color:%1;padding:8px 12px;border-radius:8px;}"
             "QMenu::item:selected{background:%2;}"
             "QProgressBar{background:%2;border:1px solid %3;border-radius:10px;text-align:center;color:%6;height:18px;}"
             "QProgressBar::chunk{background:%7;border-radius:10px;}"
             "QHeaderView::section{background:rgba(0,0,0,0.18);color:rgba(255,255,255,0.78);font-weight:700;padding:6px;border:0px;border-bottom:1px solid %3;}"
             "QTableWidget{background:transparent;gridline-color:rgba(255,255,255,0.08);color:%1;}"
             "QTableWidget::item{padding:6px;border-bottom:1px solid rgba(255,255,255,0.06);}"
             "QTableCornerButton::section{background:transparent;border:0px;}")
      .arg(text, card, border, bg, card2, muted, accent);
}

void AppConfig::applyEffectsGlobalTheme()
{
  QPalette pal = qApp->palette();
  pal.setColor(QPalette::Window, effectsBg());
  pal.setColor(QPalette::Base, QColor(0, 0, 0, 0));
  pal.setColor(QPalette::AlternateBase, QColor(0, 0, 0, 0));
  pal.setColor(QPalette::Text, effectsText());
  pal.setColor(QPalette::Button, effectsCard());
  pal.setColor(QPalette::ButtonText, effectsText());
  pal.setColor(QPalette::Highlight, effectsAccent());
  pal.setColor(QPalette::HighlightedText, effectsBg());
  qApp->setPalette(pal);
  qApp->setStyleSheet(effectsGlobalStyleSheet());
}

namespace
{
  class GlassCardHover final : public QObject
  {
  public:
    explicit GlassCardHover(QWidget *target) : QObject(target), m_target(target)
    {
      if (!m_target)
        return;

      m_shadow = new QGraphicsDropShadowEffect(m_target);
      m_shadow->setOffset(0, 12);
      m_shadow->setBlurRadius(26);
      m_shadow->setColor(QColor(0, 0, 0, 102));
      m_target->setGraphicsEffect(m_shadow);

      m_blur = new QPropertyAnimation(m_shadow, "blurRadius", this);
      m_blur->setDuration(160);
      m_color = new QPropertyAnimation(m_shadow, "color", this);
      m_color->setDuration(160);

      m_target->setAttribute(Qt::WA_Hover, true);
      m_target->installEventFilter(this);
    }

  protected:
    bool eventFilter(QObject *watched, QEvent *event) override
    {
      if (watched != m_target || !m_shadow || !event)
        return QObject::eventFilter(watched, event);

      if (event->type() == QEvent::Enter)
      {
        animateTo(true);
      }
      else if (event->type() == QEvent::Leave)
      {
        animateTo(false);
      }
      return QObject::eventFilter(watched, event);
    }

  private:
    void animateTo(bool hover)
    {
      if (!m_shadow)
        return;

      if (m_blur->state() == QAbstractAnimation::Running)
        m_blur->stop();
      if (m_color->state() == QAbstractAnimation::Running)
        m_color->stop();

      const qreal endBlur = hover ? 34.0 : 26.0;
      QColor endColor = hover ? AppConfig::effectsAccent() : QColor(0, 0, 0, 102);
      endColor.setAlpha(hover ? 74 : endColor.alpha());

      m_blur->setStartValue(m_shadow->blurRadius());
      m_blur->setEndValue(endBlur);
      m_blur->start();

      m_color->setStartValue(m_shadow->color());
      m_color->setEndValue(endColor);
      m_color->start();
    }

    QWidget *m_target = nullptr;
    QGraphicsDropShadowEffect *m_shadow = nullptr;
    QPropertyAnimation *m_blur = nullptr;
    QPropertyAnimation *m_color = nullptr;
  };

  class ToastHostWindow final : public QWidget
  {
  public:
    explicit ToastHostWindow(QWidget *parent = nullptr) : QWidget(parent) {}

    void setPanel(QWidget *panel) { m_panel = panel; }

    int blurRadiusPx() const { return 40; }
    int offsetYPx() const { return 18; }

  protected:
    void paintEvent(QPaintEvent *) override
    {
      if (!m_panel)
        return;

      QPainter p(this);
      p.setRenderHint(QPainter::Antialiasing, true);
      p.setPen(Qt::NoPen);

      const QRectF pr = m_panel->geometry();
      const QRectF base = pr.translated(0.0, static_cast<qreal>(offsetYPx()));
      const qreal radius = 14.0;
      const int layers = 18;
      const qreal blur = static_cast<qreal>(blurRadiusPx());

      for (int i = layers; i >= 1; --i)
      {
        const qreal t = static_cast<qreal>(i) / static_cast<qreal>(layers);
        const qreal spread = blur * (1.0 - t);
        const qreal a = 0.40 * t * t;
        QColor c(0, 0, 0);
        c.setAlphaF(a);
        p.setBrush(c);
        const QRectF r = base.adjusted(-spread, -spread, spread, spread);
        p.drawRoundedRect(r, radius + spread, radius + spread);
      }
    }

  private:
    QWidget *m_panel = nullptr;
  };
}

void AppConfig::installGlassCard(QWidget *card)
{
  if (!card)
    return;
  new GlassCardHover(card);
}

void AppConfig::showToast(QWidget *anchor, const QString &title, const QString &desc, int durationMs)
{
  QWidget *host = anchor ? anchor->window() : nullptr;
  if (!host)
    host = QApplication::activeWindow();
  if (!host)
    return;

  auto *toast = new ToastHostWindow(nullptr);
  toast->setAttribute(Qt::WA_DeleteOnClose, true);
  toast->setAttribute(Qt::WA_ShowWithoutActivating, true);
  toast->setAttribute(Qt::WA_TranslucentBackground, true);
  toast->setWindowFlags(Qt::Tool | Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint);
  toast->setFocusPolicy(Qt::NoFocus);

  const int blur = toast->blurRadiusPx();
  const int offY = toast->offsetYPx();

  auto *outer = new QVBoxLayout();
  outer->setContentsMargins(blur, blur, blur, blur + offY);
  outer->setSpacing(0);
  toast->setLayout(outer);

  auto *panel = new QWidget(toast);
  panel->setObjectName(QStringLiteral("toast_panel"));
  panel->setStyleSheet(
      "QWidget#toast_panel{border-radius:14px;border:1px solid rgba(255,255,255,0.14);background:rgba(0,0,0,0.55);}");
  panel->setFixedWidth(320);
  toast->setPanel(panel);
  outer->addWidget(panel);

  auto *vl = new QVBoxLayout();
  vl->setContentsMargins(12, 12, 12, 12);
  vl->setSpacing(0);
  panel->setLayout(vl);

  auto *top = new QHBoxLayout();
  top->setContentsMargins(0, 0, 0, 0);
  top->setSpacing(8);
  vl->addLayout(top);

  auto *t = new QLabel(title, toast);
  t->setStyleSheet(
      "QLabel{background:transparent;border:0px;font-weight:800;font-size:13px;letter-spacing:0.2px;color:rgba(255,255,255,0.92);}");
  top->addWidget(t, 1);

  auto *closeBtn = new QPushButton(toast);
  closeBtn->setCursor(Qt::PointingHandCursor);
  closeBtn->setFlat(true);
  closeBtn->setText(QStringLiteral("×"));
  closeBtn->setFixedSize(16, 16);
  closeBtn->setStyleSheet(
      "QPushButton{background:transparent;color:rgba(255,255,255,0.72);padding:0px;font-size:12px;font-weight:900;border-radius:8px;}"
      "QPushButton:hover{background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.92);}"
      "QPushButton:pressed{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.86);}");
  QObject::connect(closeBtn, &QPushButton::clicked, toast, [toast]()
                   { toast->close(); });
  top->addWidget(closeBtn, 0, Qt::AlignRight | Qt::AlignTop);

  if (!desc.trimmed().isEmpty())
  {
    vl->addSpacing(6);
    auto *d = new QLabel(desc, toast);
    d->setWordWrap(true);
    d->setStyleSheet(
        "QLabel{background:transparent;border:0px;font-size:12px;line-height:1.45;color:rgba(255,255,255,0.72);}");
    vl->addWidget(d);
  }

  toast->adjustSize();
  const int margin = 16;
  const QSize s = toast->size();
  const QPoint hostBR = host->mapToGlobal(QPoint(host->width(), host->height()));
  const QPoint endPos(hostBR.x() - s.width() - margin, hostBR.y() - s.height() - margin);
  const QPoint startPos(endPos.x(), endPos.y() + 6);
  toast->move(startPos);
  toast->setWindowOpacity(0.0);
  toast->show();
  toast->raise();

  QEasingCurve ease(QEasingCurve::BezierSpline);
  ease.addCubicBezierSegment(QPointF(0.25, 0.1), QPointF(0.25, 1.0), QPointF(1.0, 1.0));

  auto *fadeIn = new QPropertyAnimation(toast, "windowOpacity", toast);
  fadeIn->setDuration(220);
  fadeIn->setStartValue(0.0);
  fadeIn->setEndValue(1.0);
  fadeIn->setEasingCurve(ease);

  auto *moveIn = new QPropertyAnimation(toast, "pos", toast);
  moveIn->setDuration(220);
  moveIn->setStartValue(startPos);
  moveIn->setEndValue(endPos);
  moveIn->setEasingCurve(ease);

  fadeIn->start(QAbstractAnimation::DeleteWhenStopped);
  moveIn->start(QAbstractAnimation::DeleteWhenStopped);

  QTimer::singleShot(qMax(800, durationMs), toast, [toast]()
                     {
    auto *fadeOut = new QPropertyAnimation(toast, "windowOpacity", toast);
    fadeOut->setDuration(200);
    fadeOut->setStartValue(toast->windowOpacity());
    fadeOut->setEndValue(0.0);
    QEasingCurve ease2(QEasingCurve::BezierSpline);
    ease2.addCubicBezierSegment(QPointF(0.25, 0.1), QPointF(0.25, 1.0), QPointF(1.0, 1.0));
    fadeOut->setEasingCurve(ease2);
    QObject::connect(fadeOut, &QPropertyAnimation::finished, toast, [toast]() { toast->close(); });
    fadeOut->start(QAbstractAnimation::DeleteWhenStopped); });
}

void AppConfig::showToastAction(QWidget *anchor, const QString &title, const QString &desc,
                                const QString &actionText, const std::function<void()> &onAction,
                                int durationMs)
{
  QWidget *host = anchor ? anchor->window() : nullptr;
  if (!host)
    host = QApplication::activeWindow();
  if (!host)
    return;

  auto *toast = new ToastHostWindow(nullptr);
  toast->setAttribute(Qt::WA_DeleteOnClose, true);
  toast->setAttribute(Qt::WA_ShowWithoutActivating, true);
  toast->setAttribute(Qt::WA_TranslucentBackground, true);
  toast->setWindowFlags(Qt::Tool | Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint);
  toast->setFocusPolicy(Qt::NoFocus);

  const int blur = toast->blurRadiusPx();
  const int offY = toast->offsetYPx();

  auto *outer = new QVBoxLayout();
  outer->setContentsMargins(blur, blur, blur, blur + offY);
  outer->setSpacing(0);
  toast->setLayout(outer);

  auto *panel = new QWidget(toast);
  panel->setObjectName(QStringLiteral("toast_panel"));
  panel->setStyleSheet(
      "QWidget#toast_panel{border-radius:14px;border:1px solid rgba(255,255,255,0.14);background:rgba(0,0,0,0.55);}");
  panel->setFixedWidth(320);
  toast->setPanel(panel);
  outer->addWidget(panel);

  auto *vl = new QVBoxLayout();
  vl->setContentsMargins(12, 12, 12, 12);
  vl->setSpacing(0);
  panel->setLayout(vl);

  auto *top = new QHBoxLayout();
  top->setContentsMargins(0, 0, 0, 0);
  top->setSpacing(8);
  vl->addLayout(top);

  if (!title.trimmed().isEmpty())
  {
    auto *t = new QLabel(title, toast);
    t->setStyleSheet(
        "QLabel{background:transparent;border:0px;font-weight:800;font-size:13px;letter-spacing:0.2px;color:rgba(255,255,255,0.92);}");
    top->addWidget(t, 1);
  }
  else
  {
    top->addStretch(1);
  }

  auto *closeBtn = new QPushButton(toast);
  closeBtn->setCursor(Qt::PointingHandCursor);
  closeBtn->setFlat(true);
  closeBtn->setText(QStringLiteral("×"));
  closeBtn->setFixedSize(16, 16);
  closeBtn->setStyleSheet(
      "QPushButton{background:transparent;color:rgba(255,255,255,0.72);padding:0px;font-size:12px;font-weight:900;border-radius:8px;}"
      "QPushButton:hover{background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.92);}"
      "QPushButton:pressed{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.86);}");
  QObject::connect(closeBtn, &QPushButton::clicked, toast, [toast]()
                   { toast->close(); });
  top->addWidget(closeBtn, 0, Qt::AlignRight | Qt::AlignTop);

  if (!desc.trimmed().isEmpty())
  {
    vl->addSpacing(6);
    auto *d = new QLabel(desc, toast);
    d->setWordWrap(true);
    d->setStyleSheet(
        "QLabel{background:transparent;border:0px;font-size:12px;line-height:1.45;color:rgba(255,255,255,0.72);}");
    vl->addWidget(d);
  }

  if (!actionText.trimmed().isEmpty())
  {
    vl->addSpacing(10);
    auto *row = new QHBoxLayout();
    row->setContentsMargins(0, 0, 0, 0);
    row->setSpacing(8);
    vl->addLayout(row);

    auto *stage = new MagneticButtonStage(toast);
    stage->setShadowEnabled(false);
    stage->setStyleSheet(
        "QWidget{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.14);border-radius:12px;}");

    auto *btn = new QPushButton(stage);
    btn->setCursor(Qt::PointingHandCursor);
    btn->setFlat(true);
    btn->setText(actionText);
    btn->setStyleSheet(
        "QPushButton{background:transparent;color:rgba(255,255,255,0.92);padding:6px 12px;font-weight:900;letter-spacing:0.2px;}"
        "QPushButton:hover{background:rgba(255,255,255,0.08);}"
        "QPushButton:pressed{background:rgba(255,255,255,0.05);}");
    stage->setButton(btn);

    btn->adjustSize();
    const QSize hint = btn->sizeHint();
    stage->setFixedSize(hint.width() + 24, hint.height() + 24);

    QObject::connect(btn, &QPushButton::clicked, toast, [toast, onAction]()
                     {
      if (onAction)
        onAction();
      toast->close(); });

    row->addWidget(stage, 0, Qt::AlignLeft);
    row->addStretch(1);
  }

  toast->adjustSize();
  const int margin = 16;
  const QSize s = toast->size();
  const QPoint hostBR = host->mapToGlobal(QPoint(host->width(), host->height()));
  const QPoint endPos(hostBR.x() - s.width() - margin, hostBR.y() - s.height() - margin);
  const QPoint startPos(endPos.x(), endPos.y() + 6);
  toast->move(startPos);
  toast->setWindowOpacity(0.0);
  toast->show();
  toast->raise();

  QEasingCurve ease(QEasingCurve::BezierSpline);
  ease.addCubicBezierSegment(QPointF(0.25, 0.1), QPointF(0.25, 1.0), QPointF(1.0, 1.0));

  auto *fadeIn = new QPropertyAnimation(toast, "windowOpacity", toast);
  fadeIn->setDuration(220);
  fadeIn->setStartValue(0.0);
  fadeIn->setEndValue(1.0);
  fadeIn->setEasingCurve(ease);

  auto *moveIn = new QPropertyAnimation(toast, "pos", toast);
  moveIn->setDuration(220);
  moveIn->setStartValue(startPos);
  moveIn->setEndValue(endPos);
  moveIn->setEasingCurve(ease);

  fadeIn->start(QAbstractAnimation::DeleteWhenStopped);
  moveIn->start(QAbstractAnimation::DeleteWhenStopped);

  QTimer::singleShot(qMax(1200, durationMs), toast, [toast]()
                     {
    if (!toast->isVisible())
      return;
    auto *fadeOut = new QPropertyAnimation(toast, "windowOpacity", toast);
    fadeOut->setDuration(200);
    fadeOut->setStartValue(toast->windowOpacity());
    fadeOut->setEndValue(0.0);
    QEasingCurve ease2(QEasingCurve::BezierSpline);
    ease2.addCubicBezierSegment(QPointF(0.25, 0.1), QPointF(0.25, 1.0), QPointF(1.0, 1.0));
    fadeOut->setEasingCurve(ease2);
    QObject::connect(fadeOut, &QPropertyAnimation::finished, toast, [toast]() { toast->close(); });
    fadeOut->start(QAbstractAnimation::DeleteWhenStopped); });
}
