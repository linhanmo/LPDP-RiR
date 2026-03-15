#include <QApplication>
#include <functional>
#include <QFileInfo>
#include <QGuiApplication>
#include <QIcon>
#include <QPointer>
#include <QScreen>
#include <QDir>
#include <QCoreApplication>

#include "AppConfig.h"
#include "ChangePasswordDialog.h"
#include "LoginWindow.h"
#include "MainWindow.h"
#include "RegisterDialog.h"

namespace
{
  void centerWidget(QWidget *w)
  {
    if (!w)
      return;
    QScreen *screen = QGuiApplication::primaryScreen();
    if (!screen)
      return;
    QRect r = w->frameGeometry();
    r.moveCenter(screen->availableGeometry().center());
    w->move(r.topLeft());
  }

  QString logoPath()
  {
    const QDir base(QCoreApplication::applicationDirPath());
    const QStringList rel = {
        QStringLiteral("logo/logo.png"),
        QStringLiteral("../logo/logo.png"),
        QStringLiteral("../../logo/logo.png"),
        QStringLiteral("../../../logo/logo.png"),
    };
    for (const auto &r : rel)
    {
      const QString p = QDir::cleanPath(base.filePath(r));
      if (QFileInfo::exists(p))
        return p;
    }
    return {};
  }
}

int main(int argc, char *argv[])
{
  QApplication app(argc, argv);

  AppConfig::cleanupInvalidRecords();
  AppConfig::applyEffectsGlobalTheme();

  {
    const QString p = logoPath();
    if (!p.isEmpty())
      app.setWindowIcon(QIcon(p));
  }

  QPointer<MainWindow> mainWin;

  std::function<void()> showLogin;
  showLogin = [&]()
  {
    auto *dlg = new LoginWindow();
    dlg->setWindowIcon(app.windowIcon());
    dlg->setAttribute(Qt::WA_DeleteOnClose, true);
    QPointer<LoginWindow> loginPtr = dlg;

    QObject::connect(dlg, &LoginWindow::registerRequested, dlg,
                     [dlg](const QString &lang, int themeIndex)
                     {
                       RegisterDialog rd(lang, themeIndex, dlg);
                       rd.exec();
                     });

    QObject::connect(dlg, &LoginWindow::changePasswordRequested, dlg,
                     [dlg](const QString &username, const QString &lang, int themeIndex)
                     {
                       ChangePasswordDialog cd(username, lang, themeIndex, dlg);
                       cd.exec();
                     });

    QObject::connect(dlg, &QDialog::accepted, &app, [&]()
                     {
      const QString user = AppConfig::currentUser();
      mainWin = new MainWindow();
      mainWin->setWindowIcon(app.windowIcon());
      mainWin->resize(1280, 960);
      mainWin->setUsername(user);
      centerWidget(mainWin);
      mainWin->show();

      QObject::connect(mainWin, &MainWindow::logoutRequested, mainWin, [&]() {
        AppConfig::setCurrentUser(QString());
        if (mainWin) {
          mainWin->close();
          mainWin->deleteLater();
          mainWin = nullptr;
        }
        showLogin();
      });

      QObject::connect(mainWin, &MainWindow::changePasswordRequested, mainWin, [&]() {
        if (!mainWin) return;
        ChangePasswordDialog cd(mainWin->username(), mainWin->language(), AppConfig::themeIndex(),
                                mainWin);
        cd.exec();
      }); });

    QObject::connect(dlg, &QDialog::rejected, &app, [&]()
                     { app.quit(); });

    centerWidget(dlg);
    dlg->show();
  };

  showLogin();
  return app.exec();
}
