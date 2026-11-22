# 哈基米小姐（Gemini 猫娘）桌宠：Windows 11

本包包含完整 10 组透明版加倍动作素材（130 帧 RGBA PNG），不含原始生成图或账号凭证。它是源码运行与 PyInstaller 构建包，尚不包含预编译 EXE，也尚未在 Windows 11 实机运行验证。

1. 安装 Python 3.10 或更新版本，并确认 Python Launcher（`py`）可用。
2. 双击 `setup.bat`，会在本目录创建 `.venv` 并联网安装 `PyQt5` 与 `PyInstaller`。
3. 双击 `standalone.bat` 独立启动桌宠，或双击 `follow-antigravity.bat` 随 `Antigravity.exe` 启动和退出。
4. 如需生成独立 EXE，双击 `build.bat`，保留生成的整个 `dist\GeminiCatgirl` 文件夹，之后启动脚本会自动优先运行该 EXE。

## 交互与功能
- 跟随模式检测 Windows 进程 `Antigravity.exe`（排除 `--type=`、语言服务与 sidecar 子进程）；勾选右键「开机启动」会写入当前用户的 Windows 启动项（`HKCU\...\Run\GeminiCatgirlDesktopPet`），移动或删除解压目录后请重新设置。
- 右键菜单支持：`立即睡觉`、`叫醒`、`查询额度`、`查看上下文状态`、`查看 Antigravity 状态`、`开机启动`、`预览动作`、`退出`。
- 自动读取 `%USERPROFILE%\.gemini\antigravity\brain` 会话日志，以及 `antigravity-pulse` / `account-switcher` 插件持久化的本地统计与配额快照（仅读取非凭证展示字段）；无数据时不会编造。
