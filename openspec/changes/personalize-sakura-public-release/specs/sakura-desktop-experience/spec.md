# Sakura desktop experience

## Purpose

提供一致的佐仓三叶桌宠界面、无台词弹泡的点击与拖动交互，以及可独立获取并安装的公开源码。保留已经存在的人物身份、立绘、动画与业务功能，避免公开个人配置和测试资料。

## ADDED Requirements

### Requirement: Consistent character identity
The application SHALL present Sakura Mitsuha in chat and menus, using the existing Sakura persona and keeping all current functional entry points.

#### Scenario: Open chat and menus
- **WHEN** a user opens the pet or tray menu and starts chat
- **THEN** labels and responses identify 三叶, duplicate instructional copy is absent, and chat, balance, documents, key settings, size, expression, animation preview, reset, stealth and exit remain reachable

### Requirement: Quiet pointer interaction
The application SHALL perform single-click reactions and dragging without creating a speech bubble, preserving movement, position persistence and double-click stealth.

#### Scenario: Click or drag the pet
- **WHEN** a user clicks the character or holds the left button and drags it
- **THEN** the existing reaction and movement occur with no click or pickup speech bubble, and release returns to idle

#### Scenario: Functional feedback
- **WHEN** a user requests balance or imports a document
- **THEN** existing success and failure feedback remains available

### Requirement: Reproducible attributed publication
The public repository SHALL include runnable code, current required assets, setup instructions and upstream attribution with the original MIT notice, excluding real credentials, personal documents, local configuration and caches.

#### Scenario: Fresh repository checkout
- **WHEN** a user obtains SakuraMitsuha_Desktop_Pet from GitHub
- **THEN** its README explains setup, current controls, DeepSeek configuration, document transmission and upstream origin, and required assets decode successfully

### Requirement: Preserve approved character assets
The change SHALL preserve existing persona, image and animation material contents and keep disabled actions disabled.

#### Scenario: Preservation verification
- **WHEN** the release is compared with its local pre-change snapshot
- **THEN** protected asset and animation hashes match and no disabled motion is enabled
