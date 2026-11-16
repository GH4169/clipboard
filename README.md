# X11 内存剪贴板历史

50 条去重文本历史，只记录 CLIPBOARD，PRIMARY 不自动入历史。Ctrl+Shift+J、Ctrl+Alt+H、Ctrl+Alt+V 同时注册，j/k 或方向键选中，Enter/单击设置 CLIPBOARD/PRIMARY 并用 Shift+Insert 粘贴；Esc、Ctrl+C、再次热键和失焦取消。不保存历史到磁盘，不打印正文。

## 安装与运行

```sh
bash install.sh
bin/clipboard-history --ensure-running
bin/clipboard-history --check
```

当前仅运行于 Codex 独立 X11 桌面 :97，不获取 Windows 鼠标/键盘焦点，也不替换现有 clipboard-shelf。每个 X server 通过选择占用单实例，:99/:99.0 等别名不会重复。已启用用户 systemd 服务，下次会话启动；保留已经运行的 owner 和历史，安装时不重启。

运行依赖 Python 标准库 Tkinter、libX11/libXtst 和 CJK 字体；没有 pip/GTK 包依赖。目标机缺少 Tkinter 且 sudo 需要认证，本次通过发行版签名包源下载匹配的 python3.14-tk 并解包到用户目录，包装器自动接入。其他机器建议安装本机 Python 版本的 Tkinter，而不要复制该二进制。

Shell 可选 source autostart.sh/autostart.csh，后台 timeout 8 秒，不阻塞提示符。系统服务和日志目录使用私有权限。日志只写错误，不写正文。

## 测试

```sh
python3 -m unittest test_history.py
# 仅在专用 X11 显示中运行
DISPLAY=:99 python3 test_x11.py
```

内存去重/中文/50 条上限以及独立 Xvnc 并发启动、显示别名均已验证。弹出窗口的所有应用粘贴、图片/富文本、远程桌面热键未全面测试。此实现是 X11 文本后端；不宣称支持 Windows 原生、Wayland-only、截图历史。

## ETX

`python3 etx_clipboard_bridge.py --check` 检测当前用户/显示的 ETX。当前 WSL 没有 ETX，桥保持关闭。没有原 ETX 代理的已验证符号布局，**未实现内存提取修复**；入口安全跳过，不触碰 /proc 内存或剪贴板所有权。未来需要专门适配并验证版本/格式/竞态，不能从指南猜地址。

## 停用与卸载

```sh
systemctl --user disable clipboard-history.service
```

移除对应 source/服务/启动器。正在运行的历史保留到退出；明确 stop/restart 会清空内存。`restart_clipboard.py` 仅匹配当前用户、当前 DISPLAY 和完整脚本路径；不要随意执行。一般应用不支持 Shift+Insert 时自行使用正常粘贴。GVim 需要时按指南单独添加 Insert/命令模式的 Shift+Insert 映射。

独立 Git 管理；源码 MIT；不提交历史、日志、缓存或用户登录数据。
