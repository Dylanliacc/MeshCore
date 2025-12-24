# MeshCore Test Controller

跨平台串口测试控制工具，支持 Linux / Windows / macOS。

## 功能

- 🔌 串口自动检测与连接
- 📊 一键控制 (Test Status / Config / Log Dump / Reboot)
- 💻 CLI 模式进入
- 📝 实时日志显示与导出
- 🌙 现代深色主题 UI

## 运行方式

### 从源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 打包为可执行文件

在各平台上分别运行：

```bash
# 安装打包依赖
pip install pyinstaller

# 打包
python build.py

# 清理
python build.py clean
```

打包结果：

- **Linux**: `dist/MeshCore_Test`
- **Windows**: `dist/MeshCore_Test.exe`
- **macOS**: `dist/MeshCore_Test.app`

## 使用说明

1. 选择串口并点击「连接」
2. 点击「CLI 模式」进入命令模式
3. 使用控制按钮发送命令
4. 日志自动显示，可导出保存
