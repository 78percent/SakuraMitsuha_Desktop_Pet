# SakuraMitsuha Desktop Pet · 佐仓三叶

<p align="center">
  <img src="assets/reference/character_v1.png" alt="佐仓三叶原始立绘" height="320">
</p>

一个以佐仓三叶为角色的 Windows 桌宠。黑色长发、狐狸耳朵与旧黑长袍，安静地陪你工作，也可以通过 DeepSeek 和你聊天。

本项目基于 [kmjs1915/CeTaPet-AI-DeskTopPet-DeepSeek](https://github.com/kmjs1915/CeTaPet-AI-DeskTopPet-DeepSeek) 二次开发，替换了角色人设与图片素材，加入三叶的分层动画、表情和隐身效果，并整理了聊天界面与菜单。感谢原作者提供的桌宠、聊天和资料管理基础。

## 功能

- 分层 2D 待机、眨眼、呼吸、发摆与表情切换。
- 渐隐、现形和局部水雾般的透明效果；隐身保持动画按 60 秒循环。
- 左键拖动、窗口位置记忆、角色大小调整和系统托盘。
- DeepSeek 多轮聊天、账户余额查询、API 密钥设置。
- 导入 `.txt` / `.docx` 作为聊天参考资料。
- 单实例运行：再次启动会召回已经运行的三叶。

当前使用 Python + PySide6 的分层图片动画。默认角色高度为 180 逻辑像素；步行、游走、缩团等旧试验动作保持停用。

## 安装与启动

目前以 Windows、Python **3.11** 为运行环境。先安装 [Python 3.11](https://www.python.org/downloads/)，保留 Python Launcher，然后下载本仓库，或：

```powershell
git clone https://github.com/78percent/SakuraMitsuha_Desktop_Pet.git
cd SakuraMitsuha_Desktop_Pet
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_env.ps1
```

安装脚本会创建项目内的 `.venv`，安装固定版本依赖，并在缺少 `.env` 时生成配置文件。将自己的 DeepSeek API Key 填入根目录 `.env`：

```dotenv
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_MODEL=deepseek-flash
```

密钥可在 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取。聊天需要联网和可用的账户额度；若你的账户不支持默认模型，请将 `DEEPSEEK_MODEL` 改为账户可用的模型并重启。

双击 `start_pet.cmd` 启动。也可以运行：

```powershell
.\start_pet.cmd
```

未配置密钥时会打开设置窗口，连接验证通过后再启动。只想离线看角色和动画，可运行：

```powershell
.\start_pet.cmd --preview
```

可选：创建桌面快捷方式，之后双击“佐仓三叶”即可启动或召回：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_sakura_shortcut.ps1
```

## 操作

| 操作 | 效果 |
| --- | --- |
| 左键单击角色 | 保留轻微动作反馈，不弹出台词框 |
| 按住左键拖动 | 移动角色，松开后记住位置，不弹出台词框 |
| 左键双击角色 | 手动隐身 |
| 双击托盘图标 | 在隐身与现形之间切换 |
| 右键角色或托盘 | 打开相同的功能菜单 |
| Ctrl + 鼠标滚轮 | 调整角色大小，范围 180～720 逻辑像素 |
| 再次启动 | 召回已运行的角色 |

右键菜单提供“与三叶聊天”“资料”“DeepSeek”“角色大小”“表情”“动作预览”“待机自动隐身”“重置位置”“隐身／现形”和“退出”。

启用待机自动隐身时，角色在空闲约 15～30 分钟后短暂隐身，随后自动现形；手动隐身会持续保持，直到你主动召回。隐身时角色主体不拦截鼠标，托盘仍可操作。深色背景下痕迹可能很淡，使用托盘召回即可。

关闭聊天窗口只会隐藏窗口，当前进程中的对话仍保留。完全结束桌宠请使用右键菜单“退出”。

## 参考资料与本地数据

通过“资料 → 导入资料…”或把文件拖到角色上导入 `.txt` / `.docx`。“打开资料文件夹”可以管理已导入文件。

**导入会把原文件移动到 `CetaPet/RAG/`，请先复制需要保留在原处的文件。** 同名文件自动编号。单份资料最多加载 8,000 字，合计最多 20,000 字，超长内容会截断。

发送聊天时，当前人设、最近的对话和已加载的参考资料会发送到 DeepSeek。密钥保存在本地 `.env`，窗口位置保存在 `CetaPet/config.json`；这些文件及 `CetaPet/RAG/` 均已被 Git 忽略，不属于公开仓库。

## 项目结构

```text
CetaPet/
  main.py                 聊天、资料、密钥与基础交互
  sakura_pet.py           三叶窗口、托盘和菜单
  sakura_animation.py     分层角色、人设与待机动画
  sakura_face.py          表情绘制
  sakura_material.py      隐身材质
  single_instance.py     单实例和召回
  asset_library/         角色图片及运行所需资源
assets/reference/        原始立绘参考
run_pet.py               启动入口
setup_env.ps1            环境安装
start_pet.cmd            Windows 启动器
tests/                   可离线运行的回归检查
```

`CetaPet` 目录名沿用上游结构，便于追溯与维护。历史建模试作、失败素材、临时导出及本机协作记录不纳入公开发布。

## 检查与常见问题

检查 Python、依赖、图片解码和密钥是否已配置（不输出密钥内容）：

```powershell
.\start_pet.cmd --check
```

运行公开仓库中的离线回归检查：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

- 安装失败：确认 Python 3.11 可用，检查网络后重新执行安装脚本；需要绕过当前进程代理时可加 `-NoProxy`。
- 找不到角色：双击托盘图标、再次启动快捷方式，或使用“重置位置”。
- 聊天失败：在“DeepSeek”菜单检查余额与密钥；更改密钥会先验证连接，失败时保留旧密钥。
- 启动报错：查看本地 `.bootstrap/startup_error.log`。

## 来源与许可

上游项目：[CeTaPet-AI-DeskTopPet-DeepSeek](https://github.com/kmjs1915/CeTaPet-AI-DeskTopPet-DeepSeek)，作者 **kmjs1915**。本项目在其代码基础上二次开发，并保留原始 MIT 版权和许可文本，见 [LICENSE](LICENSE) 与 [第三方说明](THIRD_PARTY_NOTICES.md)。

佐仓三叶的人设、图片与动画素材作为本项目角色内容保留。MIT 的上游代码许可不代表原作者对新增角色素材拥有权利；如需单独转载或再分发角色素材，请先确认相应素材的使用授权。
