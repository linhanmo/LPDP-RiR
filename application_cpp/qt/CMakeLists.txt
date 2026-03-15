cmake_minimum_required(VERSION 3.16)

project(LPDP_RiR_QtGui LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

get_filename_component(_repo_root "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
list(APPEND CMAKE_PREFIX_PATH "${_repo_root}/env/Library")

find_package(Qt6 COMPONENTS Widgets Gui Core Sql OpenGLWidgets QUIET)
if(Qt6_FOUND)
  set(QT_LIBS Qt6::Core Qt6::Gui Qt6::Widgets Qt6::Sql)
  if(TARGET Qt6::OpenGLWidgets)
    list(APPEND QT_LIBS Qt6::OpenGLWidgets)
  endif()
else()
  find_package(Qt5 COMPONENTS Widgets Gui Core Sql REQUIRED)
  set(QT_LIBS Qt5::Core Qt5::Gui Qt5::Widgets Qt5::Sql)
endif()

find_package(libzip CONFIG REQUIRED)

find_package(VTK CONFIG QUIET COMPONENTS
  IOImage
  FiltersModeling
  InteractionStyle
  InteractionWidgets
  GUISupportQt
)
if(NOT VTK_FOUND)
  find_package(vtk CONFIG REQUIRED COMPONENTS
    IOImage
    FiltersModeling
    InteractionStyle
    InteractionWidgets
    GUISupportQt
  )
endif()

add_executable(LPDP_RiR_QtGui
  main.cpp
  AppConfig.cpp
  MainWindow.cpp
  NavigationBar.cpp
  NavButton.cpp
  MagneticButtonStage.cpp
  HomePage.cpp
  IntroductionPage.cpp
  ModelInterfacePage.cpp
  HistoryPage.cpp
  MarkdownTableParser.cpp
  LoginWindow.cpp
  RegisterDialog.cpp
  ChangePasswordDialog.cpp
  Analyze3DWindow.cpp
)

target_include_directories(LPDP_RiR_QtGui PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(LPDP_RiR_QtGui PRIVATE
  ${QT_LIBS}
  libzip::zip
  VTK::IOImage
  VTK::FiltersModeling
  VTK::InteractionStyle
  VTK::InteractionWidgets
  VTK::GUISupportQt
)

if(COMMAND vtk_module_autoinit)
  vtk_module_autoinit(
    TARGETS LPDP_RiR_QtGui
    MODULES
      VTK::IOImage
      VTK::FiltersModeling
      VTK::InteractionStyle
      VTK::InteractionWidgets
      VTK::GUISupportQt
  )
endif()

option(ENABLE_WINDEPLOYQT "Run windeployqt after build" OFF)

if(WIN32 AND ENABLE_WINDEPLOYQT)
  set(_qt_bin_dir "")
  set(_qt_root_dir "")
  set(_qt_plugin_dir "")
  if(TARGET Qt6::Core)
    get_target_property(_qtcore_dll Qt6::Core IMPORTED_LOCATION_RELEASE)
    if(NOT _qtcore_dll)
      get_target_property(_qtcore_dll Qt6::Core IMPORTED_LOCATION)
    endif()
    if(_qtcore_dll)
      get_filename_component(_qt_bin_dir "${_qtcore_dll}" DIRECTORY)
    endif()
  elseif(TARGET Qt5::Core)
    get_target_property(_qtcore_dll Qt5::Core IMPORTED_LOCATION_RELEASE)
    if(NOT _qtcore_dll)
      get_target_property(_qtcore_dll Qt5::Core IMPORTED_LOCATION)
    endif()
    if(_qtcore_dll)
      get_filename_component(_qt_bin_dir "${_qtcore_dll}" DIRECTORY)
    endif()
  endif()

  if(_qt_bin_dir)
    get_filename_component(_qt_root_dir "${_qt_bin_dir}" DIRECTORY)
    set(_qt_plugin_dir "${_qt_root_dir}/plugins")
  endif()

  find_program(WINDEPLOYQT_EXECUTABLE windeployqt HINTS "${_qt_bin_dir}")
  if(WINDEPLOYQT_EXECUTABLE)
    add_custom_command(
      TARGET LPDP_RiR_QtGui
      POST_BUILD
      COMMAND "${CMAKE_COMMAND}" -E env
              "QT_PLUGIN_PATH=${_qt_plugin_dir}"
              "QT_QPA_PLATFORM_PLUGIN_PATH=${_qt_plugin_dir}/platforms"
              "QT_QPA_PLATFORM=windows"
              "${WINDEPLOYQT_EXECUTABLE}"
              --release
              "$<TARGET_FILE:LPDP_RiR_QtGui>"
      VERBATIM
    )
  else()
    message(WARNING "windeployqt not found. LPDP_RiR_QtGui.exe may fail to start outside Qt runtime environment.")
  endif()
endif()
