# Gemini Desktop Pet（哈基米小姐 / Gemini 猫娘桌面宠物）

参照 [codex-desktop-pet](https://github.com/rzls420420/codex-desktop-pet) 架构与打包规范，为 **Antigravity** 打造的跨平台（**Linux & Windows 11**）透明背景桌面宠物「哈基米小姐（本喵喵）」。

## 核心特性

- **10 组完整透明加倍序列帧（130 帧 RGBA PNG，`768×832`）**：
  - `idle`（12 帧平滑眨眼）、`waving`（8 帧双挥手）、`running-right` / `running-left`（各 16 帧真侧身迈腿奔跑循环）、`jumping`（10 帧抛物线跳跃）、`failed`（16 帧委屈鼓脸序列）、`waiting`（12 帧等待）、`running`（12 帧工作）、`review`（12 帧思考）、`sleep`（16 帧入睡/呼吸泡泡/伸懒腰醒来）。
- **分档帧率与丝滑刷新**：`60ms`（`16.7Hz`）重绘定时器配合分动作帧率，奔跑不跳帧、待机不急促。
- **随 Antigravity 自动启停与开机自启**：
  - Linux：`python3 -m catgirl_pet.monitor` 或 `./follow-antigravity.sh`；开机自启写入 `~/.config/autostart/gemini-catgirl-pet.desktop`。
  - Windows 11：`follow-antigravity.bat`（检测 `Antigravity.exe` 主进程）；开机自启写入当前用户注册表 `HKCU\...\Run\GeminiCatgirlDesktopPet`。
- **右键菜单与实时数据同步**：
  - `立即睡觉` / `叫醒`
  - `查询额度`：汇总 `antigravity-pulse` `usage-v1` 近 5 小时及今日真实 Token 消耗，并读取 `account-switcher` 非凭证配额快照（标明重置状态与同步时间）。
  - `查看上下文状态`：读取 `antigravity-pulse` 持久化的对话栏同源上下文占用（如 `241.6K / 512K (47%)`）与缓存命中率（如 `84.3%`）。
  - `查看 Antigravity 状态`、`开机启动`、`预览动作`、`退出`。

## 发布包使用方式（Releases）

### Linux (`gemini-desktop-pet-v1.0.0-linux.tar.gz`)
需要 Python 3.10+ 与 `PyQt5`：
```bash
tar -xzf gemini-desktop-pet-v1.0.0-linux.tar.gz
cd gemini-desktop-pet-linux
./start.sh                 # 独立启动
./follow-antigravity.sh    # 随 Antigravity 启动与退出
```

### Windows 11 (`gemini-desktop-pet-v1.0.0-win11.zip`)
需要 Python 3.10+（确认 `py` 启动器可用）：
1. 解压压缩包后双击 `setup.bat` 创建 `.venv` 并安装 `PyQt5` 与 `PyInstaller`。
2. 双击 `standalone.bat` 独立启动，或双击 `follow-antigravity.bat` 随 `Antigravity.exe` 启停。
3. 如需打包单文件夹独立 EXE，双击 `build.bat` 生成 `dist\GeminiCatgirl\GeminiCatgirl.exe`。

## 本地构建与测试

```bash
python3 -m unittest discover -s tests -v
python3 packaging/create_packages.py
```
