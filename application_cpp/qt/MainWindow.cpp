#include "MainWindow.h"

#include <QAction>
#include <QApplication>
#include <QFont>
#include <QMenu>
#include <QPainter>
#include <QStackedWidget>
#include <QVBoxLayout>
#include <QWidget>

#include "AppConfig.h"
#include "Analyze3DWindow.h"
#include "NavigationBar.h"
#include "HomePage.h"
#include "IntroductionPage.h"
#include "ModelInterfacePage.h"
#include "HistoryPage.h"

namespace
{
  struct Theme
  {
    QString nameKey;
    QColor color;
  };

  QVector<Theme> themes()
  {
    return {
        {"theme_extra_light", AppConfig::effectsBg()},
        {"theme_standard", AppConfig::effectsBg()},
        {"theme_bright", AppConfig::effectsBg()},
        {"theme_soothing", AppConfig::effectsBg()},
        {"theme_primary", AppConfig::effectsBg()},
        {"theme_night", AppConfig::effectsBg()},
    };
  }

  class BackgroundWidget final : public QWidget
  {
  public:
    explicit BackgroundWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
      setAutoFillBackground(false);
    }

  protected:
    void paintEvent(QPaintEvent *event) override
    {
      Q_UNUSED(event);
      QPainter p(this);
      p.setRenderHint(QPainter::Antialiasing, true);
      p.fillRect(rect(), AppConfig::effectsBg());

      {
        QRadialGradient g(QPointF(width() * 0.2, height() * -0.1), qMax(width(), height()) * 0.75);
        QColor c = AppConfig::effectsAccent();
        c.setAlphaF(0.18);
        g.setColorAt(0.0, c);
        QColor t = c;
        t.setAlphaF(0.0);
        g.setColorAt(0.6, t);
        p.fillRect(rect(), g);
      }
      {
        QRadialGradient g(QPointF(width() * 0.9, height() * 0.1), qMax(width(), height()) * 0.70);
        QColor c = AppConfig::effectsAccent2();
        c.setAlphaF(0.16);
        g.setColorAt(0.0, c);
        QColor t = c;
        t.setAlphaF(0.0);
        g.setColorAt(0.55, t);
        p.fillRect(rect(), g);
      }
      {
        QRadialGradient g(QPointF(width() * 0.5, height() * 1.2), qMax(width(), height()) * 0.80);
        QColor c("#50FFC4");
        c.setAlphaF(0.10);
        g.setColorAt(0.0, c);
        QColor t = c;
        t.setAlphaF(0.0);
        g.setColorAt(0.60, t);
        p.fillRect(rect(), g);
      }
    }
  };
}

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent)
{
  m_language = AppConfig::language();
  m_themeIndex = AppConfig::themeIndex();
  m_username = AppConfig::currentUser();

  m_root = new BackgroundWidget(this);
  setCentralWidget(m_root);

  auto *layout = new QVBoxLayout();
  layout->setContentsMargins(0, 0, 0, 0);
  layout->setSpacing(0);
  m_root->setLayout(layout);

  m_navbar = new NavigationBar(this);
  layout->addWidget(m_navbar);
  setUsername(m_username);

  m_stack = new QStackedWidget(this);
  layout->addWidget(m_stack, 1);

  m_home = new HomePage(this);
  m_intro = new IntroductionPage(this);
  m_model = new ModelInterfacePage(this);
  m_history = new HistoryPage(this);

  m_stack->addWidget(m_home);
  m_stack->addWidget(m_intro);
  m_stack->addWidget(m_model);
  m_stack->addWidget(m_history);

  connect(m_navbar, &NavigationBar::navigateTo, this, &MainWindow::onNavigate);
  connect(m_navbar, &NavigationBar::toggleLanguageRequested, this,
          &MainWindow::onToggleLanguage);
  connect(m_navbar, &NavigationBar::themeIndexChanged, this, &MainWindow::setThemeIndex);
  connect(m_navbar, &NavigationBar::logoutRequested, this, [this]()
          { emit logoutRequested(); });
  connect(m_navbar, &NavigationBar::changePasswordRequested, this,
          [this]()
          { emit changePasswordRequested(); });

  connect(m_home, &HomePage::navigateRequested, this, &MainWindow::onNavigate);

  connect(m_model, &ModelInterfacePage::visualize3DRequested, this,
          [this](const QString &suggestedNpzPath)
          {
            Analyze3DWindow::launchPythonGui(this, m_language, suggestedNpzPath);
          });

  applyTheme();
  updateLanguage();
  onNavigate("Homepage");
}

QString MainWindow::language() const { return m_language; }

QString MainWindow::username() const { return m_username; }

void MainWindow::setUsername(const QString &username)
{
  m_username = username;
  if (m_navbar)
  {
    m_navbar->setUsername(m_username);
  }
}

void MainWindow::setLanguage(const QString &lang)
{
  if (lang == m_language)
  {
    return;
  }
  m_language = (lang == "EN") ? "EN" : "CN";
  AppConfig::setLanguage(m_language);
  updateLanguage();
}

void MainWindow::onToggleLanguage()
{
  setLanguage(m_language == "CN" ? "EN" : "CN");
}

void MainWindow::setThemeIndex(int index)
{
  const auto list = themes();
  if (index < 0 || index >= list.size())
  {
    return;
  }
  if (index == m_themeIndex)
  {
    return;
  }
  m_themeIndex = index;
  AppConfig::setThemeIndex(m_themeIndex);
  applyTheme();
}

void MainWindow::applyTheme()
{
  AppConfig::applyEffectsGlobalTheme();
  const auto list = themes();
  QColor bg = AppConfig::effectsBg();
  if (m_themeIndex >= 0 && m_themeIndex < list.size())
  {
    bg = list[m_themeIndex].color;
  }

  QPalette pal = qApp->palette();
  pal.setColor(QPalette::Window, bg);
  pal.setColor(QPalette::Base, QColor(0, 0, 0, 0));
  pal.setColor(QPalette::AlternateBase, QColor(0, 0, 0, 0));
  pal.setColor(QPalette::Text, AppConfig::effectsText());
  pal.setColor(QPalette::Button, AppConfig::effectsCard());
  pal.setColor(QPalette::ButtonText, AppConfig::effectsText());
  qApp->setPalette(pal);

  m_root->setAutoFillBackground(false);
  m_root->setPalette(pal);
  m_root->update();

  if (m_navbar)
  {
    m_navbar->setThemeColor(bg);
  }
  if (m_home)
  {
    m_home->setThemeColor(bg);
  }
  if (m_intro)
  {
    m_intro->setThemeColor(bg);
  }
  if (m_model)
  {
    m_model->setThemeColor(bg);
  }
  if (m_history)
  {
    m_history->setThemeColor(bg);
  }
  if (m_analyze3d)
  {
    m_analyze3d->setThemeColor(bg);
  }
}

void MainWindow::updateLanguage()
{
  {
    QFont f;
    if (m_language == "EN")
    {
      f.setFamily("Arial");
      f.setPointSize(10);
    }
    else
    {
      f.setFamily("Microsoft YaHei");
      f.setPointSize(10);
    }
    qApp->setFont(f);
  }
  if (m_navbar)
  {
    m_navbar->setLanguage(m_language);
  }
  if (m_home)
  {
    m_home->setLanguage(m_language);
  }
  if (m_intro)
  {
    m_intro->setLanguage(m_language);
  }
  if (m_model)
  {
    m_model->setLanguage(m_language);
  }
  if (m_history)
  {
    m_history->setLanguage(m_language);
  }
  if (m_analyze3d)
  {
    m_analyze3d->setLanguage(m_language);
  }
}

void MainWindow::onNavigate(const QString &pageKey)
{
  if (pageKey == "Homepage")
  {
    m_stack->setCurrentWidget(m_home);
  }
  else if (pageKey == "Introduction")
  {
    m_stack->setCurrentWidget(m_intro);
  }
  else if (pageKey == "ModelInterface")
  {
    m_stack->setCurrentWidget(m_model);
  }
  else if (pageKey == "History")
  {
    m_stack->setCurrentWidget(m_history);
  }

  if (m_navbar)
  {
    m_navbar->setActivePage(pageKey);
  }
}
