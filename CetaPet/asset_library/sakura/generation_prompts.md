# 三叶动画素材制作记录

工具：内置 `image_gen.imagegen`，三次调用均设置 `transparent_background=true`。未使用 CLI、外部 API 密钥或额外模型服务。参考立绘为 `assets/reference/character_v1.png`，参考人设为同目录 `persona_clean_v1.txt`。原素材未覆盖。

## 需求与保留项

用户选择当前桌宠中的程序动画，允许适度重绘局部头发、手脚与衣物；保留脸型、狐耳、黑长发、公主切、红发带、黑袍与靴子的辨识度。运行部件由生成 atlas 按透明连通区域拆分，坐标记录在 `atlas_manifest.json`。不是 Cubism 导出文件。

## 提示词集合

1. **拆件制作 / identity-preserve**：参考原图，制作三列三行透明动画拆件图。保持相同角色、服装、柔和精细的二次元画风及比例。九格分别为完整后发、无头无手腿的长袍躯干、睁眼头部（含狐耳与红发带）、同样头部的闭眼版、画面左侧袖子与手、画面右侧袖子与手、左腿与靴子、右腿与靴子、两缕前侧长发。补全原先被遮挡的部位，禁止文字、标签、边框、背景、投影。最初要求全身画布配准，生成结果未严格满足，因此后续使用独立部件定位。
2. **透明与躯干修正 / background-extraction + precise-object-edit**：保留九个部件的位置、比例和画风，移除背景与部件外发光，必须使用实际 alpha；去掉躯干上重复的左袖与手，补全下方长袍。保持睁眼／闭眼、两只手臂、腿与前发。
3. **最终重排 / compositing，最终 atlas 使用此版本**：

> Use case compositing. Repack this animation parts atlas cleanly, DO NOT change artwork, face identity, clothes or expressions. EXACT 3x3 equal rectangular cell grid on portrait transparent image. Each isolated part must fit entirely INSIDE its cell with a generous transparent margin of at least 8% on every side. No overlap, no touching between neighboring parts! Each part can be resized to fit its own cell; fullbody registration is NOT needed. Top row: long backhair; sleeveless torso/cloak (NO arm or hand); open-eye head with ears and red ribbon. Middle row: closed-eye head IDENTICAL same size/orientation/location as open-eye head within its cell; left sleeve with hand; right sleeve with hand. Bottom row: left leg with boot; right leg with boot; pair of front hair locks. All nine distinct parts entirely separate. Bottom hair lock pair should be ONE pair, not 2 duplicated heads. Torso has NO arms, NO hands, NO sleeves; remove shoulder-cap shaped hanging sleeve on image left of torso and reconstruct cloak fabric. Actual alpha transparency, no labels, borders or text, no shadow/glow behind objects.

## 实际使用方式与限制

- 生成结果不是严格等格配准，程序按 alpha 连通区域拆件并在 `sakura_animation.PLACEMENT` 重新绑定位置；前发拆为两件，共十件。
- 动作由肩部、髋部旋转与分层网格共同完成；小幅动作适合现有正面立绘，不包含大角度转身或透视变换。
- 隐身水波扰动角色纹理与透明度，不读取或折射真实桌面背景；完全隐形时原生窗口隐藏。
- 图形接口依据 [Qt QTransform](https://doc.qt.io/qt-6/qtransform.html) 与 [透明 QWidget](https://doc.qt.io/qt-6/qwidget.html) 的能力实现。

## 表情素材 v2 与配准

运行时使用 ImageGen 生成的 `head_base.png` 干净头部（版本源文件 `face_base_v2.png`），不包含旧眼、眉、嘴。原图、`head_open.png` 和 `head_closed.png` 均保留。`face_manifest_v2.json` 记录 372×471 统一坐标与五种表情参数，`generation_v2.json` 保存内置 ImageGen 的完整提示词。

原眼部纹理由同一睁眼源图按固定区域取样，仅在眼睛打开时绘制；闭眼只画一条睫毛弧线，绝不叠加虹膜。眉形、嘴形和开合参数插值，表情变换不会叠两张脸。`tools/validate_sakura_faces.py` 导出全眨眼、表情过渡与 DPI 检查矩阵。

默认平静；拨头发略得意、整理袖口专注、点击好奇。待机表情默认每90～180秒尝试一次、持续3～6秒、约0.6秒过渡；浅笑候选权重10%，这些数值是实现默认值，用户确认的要求是安静、浅笑低频。右键「表情预览」可即时查看五种表情。
