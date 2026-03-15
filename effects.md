# ReactBits 可选效果与页面推荐

## 可选效果名

- Ghost Cursor
- Glow Border
- Gradient Blinds
- Grainient
- Grid Distortion
- Grid Motion
- Grid Scan
- Hyperspeed
- Image Trail
- Iridescence
- Laser Flow
- Letter Glitch
- Light Pillar
- Light Rays
- Lightning
- Liquid Chrome
- Liquid Ether
- Magnetic Button
- Pulse Dot
- Noise
- Orb
- Particles
- Pixel Blast
- Pixel Snow
- Plasma
- Progress Ring
- Prism
- Prismatic Burst
- Ribbons
- Ripple Grid
- Shimmer Skeleton
- Silk
- Splash Cursor
- Tilt Card
- Toast
- Typing Dots

## 按类别整理

### 1. 背景 / 氛围（低干扰）

- Noise
- Grainient
- Gradient Blinds
- Iridescence
- Grid Motion
- Grid Distortion
- Light Rays
- Light Pillar
- Liquid Ether
- Liquid Chrome
- Ribbons
- Prism
- Prismatic Burst
- Silk

### 2. 状态 / 加载（按需出现）

- Grid Scan
- Laser Flow
- Pulse Dot
- Typing Dots（更适合短驻）
- Shimmer Skeleton（骨架屏）

### 3. 交互 / 光标 / 文字（局部启用）

- Orb
- Ripple Grid
- Ghost Cursor
- Splash Cursor
- Image Trail
- Letter Glitch（更偏营销短驻）

### 4. 组件 / 控件（更偏产品化）

- Glow Border（高亮描边）
- Magnetic Button（磁吸按钮）
- Tilt Card（卡片轻 3D 倾斜）
- Toast（轻提示）

### 5. Canvas / 粒子（注意性能）

- Particles
- Hyperspeed（更适合短驻 loading）
- Progress Ring（环形进度）
- Lightning
- Pixel Snow
- Pixel Blast
- Plasma

## 按页面推荐

说明：单页别堆太多动效（建议 2–3 个以内），否则影响体验/性能。

### 1. 首页（Homepage）

- 主推（1–2 个即可）：Grainient / Noise（底纹质感）、Iridescence（极慢淡渐变）
- 可选：Grid Motion（弱网格科技感）、Light Rays（仅 Hero 区弱化）、Glow Border（强调 CTA 卡片/按钮）、Magnetic Button（只用于主按钮）
- 不建议：Splash Cursor、Image Trail、Letter Glitch（偏炫、干扰信息阅读）

### 2. 介绍页（Introduction）

- 主推：Noise / Grainient（弱底纹）、Ripple Grid（卡片/标题 hover 反馈）
- 可选：Prism（章节分隔条）、Iridescence（章节标题背景弱化）、Shimmer Skeleton（内容加载占位）
- 不建议：Hyperspeed、Pixel Blast（信息页不适合）

### 3. 模型页（Model / 推理分析页）

- 主推：Grid Scan（分析中状态隐喻）、Laser Flow（进度条/状态条）、Orb（聚焦当前切片/结果）
- 可选：Progress Ring（局部 loading）、Pulse Dot（小状态指示）、Light Pillar / Light Rays（结果页顶部弱化）、Toast（保存/导出反馈）
- 不建议：Lightning、Letter Glitch（医疗严肃性不匹配）

### 4. 历史页（History）

- 主推：Noise / Grainient（弱底纹）、Ripple Grid（列表 hover/选中反馈）
- 可选：Ribbons（页头装饰条，静态或极慢）、Toast（删除/导出等操作反馈）
- 不建议：动态背景大面积循环（影响扫读效率）

### 5. 登录 / 注册 / 修改密码

- 主推（只用 1 个）：Orb（中心聚焦表单）、Noise（提升质感）
- 可选：Silk / Liquid Ether（极慢、低对比的柔背景）、Glow Border（强调主按钮或当前表单卡片）、Shimmer Skeleton（请求中占位）
- 不建议：Ghost Cursor、Splash Cursor（输入框场景易干扰）

### 6. HTML 报告

- 主推（更产品化的组合）：Noise / Grainient（质感底纹）+ Ripple Grid（卡片/表格 hover 反馈）
- 状态动效（按需出现）：Typing Dots / Pulse Dot（生成中）+ Grid Scan（短驻）+ Laser Flow（进度/状态）
- 影像查看区（局部启用）：Image Trail 或 Splash Cursor（只在影像容器内，不要全页）
- 不建议大面积常驻：Hyperspeed、Pixel Blast、Letter Glitch、Lightning（炫但不稳重）

### 7. 3D 分析器（3D Analyzer）

- 主推：Orb（聚焦当前 3D 视图/选中目标）、Glow Border（高亮当前工具/选中对象）
- 可选：Noise / Grainient（弱底纹质感）、Ripple Grid（按钮/控件 hover 反馈）、Toast（导出/保存反馈）
- 状态动效（按需出现）：Progress Ring / Typing Dots（重建/加载中）、Pulse Dot（在线/连接状态）
- 不建议：Hyperspeed、Pixel Blast、Plasma、Lightning（大面积常驻易晕/影响观察）

### 8. Choosen
- Progress Ring (data process) ✔
- Tilt Card (main buttons) ✔
- Toast (feedback) ✔
- Magnetic Button (sub-button) ✔
- Typing Dots (reports) ✔
- Liquid Chrome (homepage) ✔