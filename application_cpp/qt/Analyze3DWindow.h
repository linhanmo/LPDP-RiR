#pragma once

#include <QColor>
#include <QString>
#include <QMainWindow>

#include <vtkSmartPointer.h>

class QLabel;
class QComboBox;
class QPushButton;
class QRadioButton;
class QFrame;
class QVTKOpenGLNativeWidget;

class vtkGenericOpenGLRenderWindow;
class vtkRenderer;
class vtkImageData;
class vtkImageImport;
class vtkImagePlaneWidget;
class vtkCallbackCommand;
class vtkImageCast;
class vtkObject;

class Analyze3DWindow final : public QMainWindow
{
  Q_OBJECT

public:
  explicit Analyze3DWindow(QWidget *parent = nullptr);

  static void launchPythonGui(QWidget *parent, const QString &lang,
                              const QString &suggestedNpzPath = QString());

  void setLanguage(const QString &lang);
  void setThemeColor(const QColor &bg);
  void openNpzFile(const QString &path);

private slots:
  void onLoadNpZ();
  void onKeyChanged(int index);
  void onOrientationChanged();

private:
  QString pick(const QString &cn, const QString &en) const;
  void applyLanguage();
  QString currentAxis() const;
  void loadKeysFromNpz(const QString &npzPath);
  void updateVisualization();
  void setOrientationAxis(const QString &axis);
  void stepSlice(int delta);
  void resetCamera();
  void resetWindowLevel();
  static void onPlaneStartInteraction(vtkObject *, unsigned long, void *, void *);
  static void onPlaneEndInteraction(vtkObject *, unsigned long, void *, void *);

  QString m_lang = "CN";
  QColor m_bg = QColor("#0B1220");

  QLabel *m_title = nullptr;
  QPushButton *m_loadBtn = nullptr;
  QLabel *m_fileLabel = nullptr;
  QLabel *m_modeLabel = nullptr;
  QComboBox *m_modeCombo = nullptr;
  QLabel *m_orientLabel = nullptr;
  QRadioButton *m_front = nullptr;
  QRadioButton *m_side = nullptr;
  QRadioButton *m_top = nullptr;
  QLabel *m_hint = nullptr;
  QFrame *m_view = nullptr;
  QVTKOpenGLNativeWidget *m_vtkWidget = nullptr;

  vtkSmartPointer<vtkGenericOpenGLRenderWindow> m_renderWindow;
  vtkSmartPointer<vtkRenderer> m_renderer;
  vtkSmartPointer<vtkImageData> m_imageData;
  vtkSmartPointer<vtkImageImport> m_importer;
  vtkSmartPointer<vtkImageCast> m_cast;
  vtkSmartPointer<vtkImagePlaneWidget> m_planeWidget;
  vtkSmartPointer<vtkCallbackCommand> m_onStartInteraction;
  vtkSmartPointer<vtkCallbackCommand> m_onEndInteraction;

  QString m_npzPath;
  QStringList m_keys;
  QByteArray m_volumeBytes;
  double m_defaultWindow = 0.0;
  double m_defaultLevel = 0.0;
};
