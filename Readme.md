# LPDP-RiR 项目说明

## 1. 环境搭建与安装

### 前置要求
- 请访问https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist?view=msvc-170 下载安装最新的 Visual C++ 运行库，并重启电脑，重启后再次运行安装程序，选择修复。
- 请确保已安装 **Anaconda**。
 打开 Windows Powershell，运行以下命令注册conda进入powershell（第二行需要输入你自己的实际路径，以E:\anaconda\shell\condabin\conda-hook.ps1为例）：
 ```powershell
 Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
 & "E:\anaconda\shell\condabin\conda-hook.ps1"
 conda init powershell
 ```
 重启Windows Powershell，使conda生效。
- **重要提示**：请确保本项目文件夹所在的完整路径中**不包含任何中文字符**（例如路径：`e:\lpdp-rir`）。

### C++/Qt 版本额外前置要求
- 安装 **Visual Studio 2022**（勾选“使用 C++ 的桌面开发”，并安装对应 Windows SDK）。
- 安装 **CMake**（建议 3.16 及以上）。

### 安装步骤

0. **批处理脚本一键安装**  
   为了简化安装过程，我们提供了一个批处理脚本 `install.bat`。用户可以通过使用管理员权限运行该脚本实现一键安装和配置环境，无需手动操作。不过该脚本存在出错的可能性，因此建议用户按照下面的步骤操作。

1. **创建虚拟环境**  
   打开 Windows Powershell，运行以下命令创建基于 Python 3.11 的虚拟环境（以E:\lpdp-rir为例）：
   ```powershell
   conda create --prefix e:\lpdp-rir\env python=3.11 -y
   ```

2. **激活环境并进入项目目录**
   ```powershell
   conda activate e:\lpdp-rir\env
   cd e:\lpdp-rir
   ```

3. **安装依赖**
   ```powershell
   pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
   conda install -c conda-forge mayavi -y
   ```

4. **（可选）安装 C++/Qt 版本编译依赖（推荐）**
   ```powershell
   conda install -c conda-forge qt6-main vtk libzip -y
   ```

### 使用 uv 创建 Python 虚拟环境（替代 conda）
`uv` 只管理 Python 依赖；不会提供 `libzip/Qt/VTK` 的 CMake 包（例如 `libzipConfig.cmake` / `Qt6Config.cmake` / `VTKConfig.cmake`）。如果你用 `uv/.venv` 运行 CMake，遇到 “找不到 libzip/Qt/VTK”，属于正常现象，需要用下文的 vcpkg 或 conda 给 CMake 提供 C++ 依赖。

1. 安装 uv（任选其一）
```powershell
pip install -U uv
```

2. 在项目根目录创建虚拟环境（示例使用 `uv/.venv`）
```powershell
cd e:\LPDP-RiR
uv venv uv\.venv --python 3.11
```

3. 安装 Python 依赖
```powershell
uv pip install -r requirements.txt
```

## 2. 数据集下载

请访问以下百度网盘链接下载项目提供的数据：
- **下载链接**: [https://pan.baidu.com/s/18WE9rPLZcDkgPIy9M4gKcg?pwd=8888]
- **提取码**: `8888`

## 3. 运行说明

### 启动软件
1. 进入 `application` 文件夹。
2. 运行 `main.py` 启动程序。

**推荐运行方式**：  
建议使用 **VS Code** 打开本项目文件夹。确保 Python 解释器已选择为你使用的 Python 环境（conda 的 `e:\lpdp-rir\env` 或 uv 的 `uv\.venv`），打开 `application/main.py` 后选择右上角的"运行 Python 文件"按钮。这能确保环境变量被正确加载。

**命令行运行方式**：  
在项目根目录下，打开 Windows Powershell，运行以下命令：
```powershell
conda activate e:\lpdp-rir\env
cd application
python main.py
```

如果你使用的是 uv 虚拟环境（示例 `uv/.venv`），可以这样运行：
```powershell
cd e:\LPDP-RiR
.\uv\.venv\Scripts\activate
cd application
python main.py
```

### 启动 C++ Qt GUI（推荐）
#### Python 环境说明（uv vs conda）
- Python 环境只用于运行 Python 端逻辑（模型推理/3D VTK 查看器）。
- C++/Qt 编译依赖（libzip/Qt/VTK）必须能被 CMake 发现：要么来自 vcpkg，要么来自 conda 的 `Library` 前缀。

#### conda 编译
1. 在项目根目录打开 Windows Powershell，并激活 conda 环境：
```powershell
conda activate e:\lpdp-rir\env
cd e:\lpdp-rir
```

2. 配置并编译（Release）：
```powershell
cmake -S "e:\LPDP-RiR\application_cpp\qt" -B "e:\LPDP-RiR\application_cpp\qt\build" `
  -DCMAKE_PREFIX_PATH="e:\lpdp-rir\env\Library"
cmake --build "e:\LPDP-RiR\application_cpp\qt\build" --config Release
```

3. 运行 C++ 版本主程序：
```powershell
& "e:\LPDP-RiR\application_cpp\qt\build\Release\LPDP_RiR_QtGui.exe"
```

4. 3D 可视化说明：
- C++ Qt 界面负责整体 UI；3D 的数据解析与交互由 Python 端（VTK）负责。点击“3D可视化”会自动调用本项目配置的 Python 环境启动 3D 查看器（uv 或 conda 均可）。
- 若 3D 窗口无法打开，可在已激活的 conda 环境中检查依赖：
```powershell
python -c "import vtk, win32gui; print('ok')"
```

#### vcpkg 安装 C++ 依赖 + CMake toolchain
这条路线适合你现在 Python 用 `uv/.venv`，同时又希望 CMake 能稳定找到 libzip/Qt/VTK 的场景。

1) 安装 vcpkg（只需一次）
```powershell
cd d:\
git clone "https://github.com/microsoft/vcpkg"
cd d:\vcpkg
.\bootstrap-vcpkg.bat
```

如果你系统里没有 Git（`git clone` 无法执行），先安装 Git for Windows（安装时选择 “Git from the command line and also from 3rd-party software”，确保加入 PATH），安装后重新打开 PowerShell 验证：
```powershell
git --version
```

也可以不装 Git，直接下载 vcpkg 的 zip（示例）：
```powershell
cd d:\
Invoke-WebRequest -Uri "https://github.com/microsoft/vcpkg/archive/refs/heads/master.zip" -OutFile "vcpkg.zip"
Expand-Archive -Force "vcpkg.zip" "d:\"
Rename-Item "d:\vcpkg-master" "d:\vcpkg"
cd d:\vcpkg
.\bootstrap-vcpkg.bat
```

2) 安装 C++ 依赖（至少 libzip；通常还需要 Qt6 + VTK）
```powershell
d:\vcpkg\vcpkg.exe install libzip:x64-windows
d:\vcpkg\vcpkg.exe install qtbase:x64-windows
d:\vcpkg\vcpkg.exe install vtk:x64-windows
```

3) 重新配置并编译（重点是加 toolchain）
```powershell
Remove-Item -Recurse -Force e:\LPDP-RiR\application_cpp\qt\build

cmake -S "e:\LPDP-RiR\application_cpp\qt" `
  -B "e:\LPDP-RiR\application_cpp\qt\build" `
  -G "Visual Studio 17 2022" -A x64 `
  -DCMAKE_TOOLCHAIN_FILE="d:\vcpkg\scripts\buildsystems\vcpkg.cmake" `
  -DVCPKG_TARGET_TRIPLET=x64-windows

cmake --build "e:\LPDP-RiR\application_cpp\qt\build" --config Release
```

4) 运行 C++ 版本主程序
```powershell
& "e:\LPDP-RiR\application_cpp\qt\build\Release\LPDP_RiR_QtGui.exe"
```

### 登录信息
- **注册**：新用户可在软件登录界面直接注册账号。
- **测试账号**：
  - 用户名：`lin`
  - 密码：`111`

## 4. 版本更新说明
- **beta1.0**：新增了LPDP-RIR模型的应用功能。
- **beta1.1**：新增了ACX-UNet模型的应用功能。
- **beta2.0**：新增了对npz文件的3D可视化功能和GUI页面。
- **beta2.1**：对3D可视化功能进行了优化，新增了交互功能。
- **beta3.0**：新增了登录注册逻辑。
- **beta4.0**：新增了用户数据存储和读取功能。
- **beta5.0**：新增了登录注册页面的GUI页面。
- **beta5.1**：新增了模型应用界面的GUI页面。
- **beta6.0**：新增了历史记录访问功能。
- **beta6.1**：新增了历史记录访问的GUI页面。
- **beta6.2**：预设了首页和产品介绍页的GUI页面。
- **v1.0**：正式发布版本，实现了完整的交互逻辑和页面切换逻辑。
- **v1.1**：修复了主程序与数据库交互的一些bug。
- **v2.0**：新增了用户退出登录的功能。
- **v2.1**：新增了用户修改密码的功能。
- **v2.2**：新增了用户注销账号的功能。
- **v3.0**：新增了中英文切换的功能。
- **v4.0**：新增了对本地文件夹路径检查的功能，及时删除数据库中不存在的路径。
- **v4.1**：修复了主程序与数据库交互的一些bug。
- **v4.2**：修复了在3D可视化中会弹出VTKoutputwindow从而影响用户使用体验的问题。
- **v4.3**：修正了readme中的一些错误表述，修复了requirements中的部分库的版本错误。
- **v5.0**：加入ico文件，软件运行时可以显示软件的logo图标。
- **v5.1**：修正了requirements中的部分库的版本错误，并修复了一些bug。
- **v6.0**：使用tkinker框架重构了GUI界面，避免运行库版本冲突导致的部分bug。
- **v6.1**：添加了批处理脚本，用户可以通过使用管理员权限运行该脚本实现一键安装和配置环境，无需手动操作。
- **v6.2**：中英文切换功能回归，用户可以实时切换中文页面和英文页面。
- **v6.3**：给中英文切换增加了记忆功能，默认为中文，下一次打开软件时会自动切换到上次使用的语言。
- **v6.4**：在登录时新增了"记住我的功能"，用户选择"记住我"后，下次登录时会自动填充账号密码。
- **v6.5**：新增了切换主题颜色的功能。
- **v6.6**：给主题颜色切换增加了记忆功能，默认为标准医疗蓝，下一次打开软件时会自动切换到上次使用的主题颜色。
- **v7.0**: 新增了更专业的病灶分析功能。
- **v7.1**: 新增了专业病理学分析的功能。
- **v7.2**: 新增了手术路径规划功能。
- **v7.3**: 修改了模型生成的报告的样式，模型将不再之进行图像分割，而是会额外进行病灶分析、病理学分析，并给出诊断意见，必要时会给出手术路径规划。
- **v7.4**: 更新了requirements.txt，新增了nibabel库的版本要求。
- **v8.0**: 引入更专业的开源数据库的数据，完善模型的病理分析、治疗建议和手术路径规划的功能。
- **v8.1**: 改进了生成报告的模块，现在可以同时导出pdf和html两种格式的报告。
- **v8.2**: 更新了requirements.txt，新增了reportlab库的版本要求。
- **v8.3**: 新增了批量化处理文件，用户可以用跑批文件batch_process.py快速获得模型处理结果与报告，用collect_reports.py快速提取所有报告。
- **v8.4**: 在报告中新增了TNM分期表、随访建议表。
- **v8.5**: 优化了报告的部分细节。
- **v8.6**: 搭建了简单的homepage和introduction。
- **v8.7**: 将模型使用页面的报告栏改为了显示报告摘要。
- **v8.8**: 历史记录页面进入后立即刷新，不会存在数据滞后性。
- **v8.9**: 加入了一些基于tkinker的动态效果和静态效果。
- **v9.0**: 用纯C++的QT重写了GUI。
- **v9.1**: 用纯C++实现了部分后端的逻辑，实现一定程度上的性能优化。
- **v9.2**: 新增了进程与线程管理，修复了一些bug。


### 如果遇到难以解决的问题，请联系开发者获取帮助。
