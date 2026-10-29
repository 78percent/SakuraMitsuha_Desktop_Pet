# v11 桌宠接入

- 来源：`D:/mesh-avatar-studio/projects/sakura-fresh-v1/native/export-v11-repair/` 的 Cubism 导出。
- 参数轨迹：`native/runtime-stress-v11/eyes-samples.json`，6 秒、30 Hz、180 个循环区间，末帧只供闭环核对。
- 本次桌宠播放同一版 moc3 经独立 Cubism SDK 渲染出的 WebP 帧；moc3、纹理和参数轨迹也随包保留。
- 原生实时渲染器已编写，但本机后台创建 OpenGL 上下文触发访问冲突，不能作为当前默认适配器。
- 用户在 2026-10-29 授权先接入此 v11 循环，进一步视觉调教待回家后进行。
- v11 腿根、髋骨骼和嘴部获得局部认可；整模型、眼角与头发连接尚未获得整体认可。
- 本目录的 `runtime-ready` 只表示帧播放路径通过运行验证，不表示实时 Live2D 或整模型视觉验收。

## 2026-10-29 实测

- `validate_package` 读回 12 项资源及 SHA-256，WebP 为 181 帧，循环使用前 180 帧。
- 180 帧按顺序离屏读取：180 像素档中位 11.64 ms、p95 20.61 ms；720 像素档中位 13.06 ms、p95 21.93 ms。这是渲染调用耗时，不是屏幕帧率。
- 30 项切换相关测试通过，包含实际 v11 包载入、首帧、返回 Q版、配置回退、右键菜单和同一尺寸档。
- `openspec validate design-sakura-cubism-alternate-model --strict` 通过。
- 新版桌宠进程已启动，Windows 报告主窗口“佐仓三叶”响应正常；Computer Use 的窗口清单没有列出透明工具窗口，本轮未取得桌面画面目视证据。
