# Proposal

## Why

当前桌宠已有三叶人设、立绘和动画，但共享界面仍残留上游鲸鱼娘文案，README 混有大量迭代记录。用户明确要求整理为自己的项目并发布公开 GitHub 仓库。

## What Changes

- 统一聊天、状态和菜单文案，精简重复说明，保留现有功能入口。
- 删除单击和拖拽的随机台词及弹泡调用，保留动作、位置保存和双击隐身。
- 重写面向使用者的 README，注明上游二开和 MIT 版权。
- 排除密钥、个人资料、缓存和本地历史预览，发布 `78percent/SakuraMitsuha_Desktop_Pet` 公开仓库。
- 原始素材、人设、动画、材质及既有禁用状态保持；历史记录留在本地，不篡改视觉验收。

## Capabilities

### New Capabilities
- `sakura-desktop-experience`: 三叶界面身份、安静的鼠标交互和可复现公开交付。

### Modified Capabilities
无已归档主规范；本变更独立记录，不覆盖历史材质与建模变更。

## Impact

主要修改 `CetaPet/main.py`、`CetaPet/sakura_pet.py`、README、发布忽略规则及交互测试。不改变 API 协议、依赖版本、人物素材、动画参数或 Godot 试作。用户本轮已授权实现、创建公开仓库和 push。
