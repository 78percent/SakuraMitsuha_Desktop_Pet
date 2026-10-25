# 来源与第三方说明

## CeTaPet

- 项目：<https://github.com/kmjs1915/CeTaPet-AI-DeskTopPet-DeepSeek>
- 作者：kmjs1915
- 本地最初导入版本：`d0725b0e0aa58cd547c48b1681988ee708120d31`
- 许可：MIT，原始文本保留在根目录 `LICENSE` 和 `CetaPet/LICENSE`。

SakuraMitsuha Desktop Pet 基于上述项目二次开发。上游提供了桌宠窗口、DeepSeek 聊天、余额查询、API 密钥设置和资料管理等基础；本项目加入佐仓三叶的人设、角色素材、分层动画、表情、隐身效果、单实例召回及专属界面。

`CetaPet/asset_library/move/` 等上游兼容资源保留用于共享基础代码；默认角色由 `sakura_pet.py` 和三叶资源绘制。上游许可及作者署名并未因界面更名而移除。

## Python 依赖

依赖版本列于 `requirements.txt`，各自遵循其发行包许可，包括 Qt/PySide6、NumPy、Requests 与 python-dotenv。安装脚本直接安装官方 Python 包，不在本仓库重新打包其二进制发行物。

## 角色素材

三叶角色素材与人设来自本项目既有内容，保持原文件。它们不应归为上游作者原创，也不应仅凭上游 MIT 许可推定独立素材授权。
