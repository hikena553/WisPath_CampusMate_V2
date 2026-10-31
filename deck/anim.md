# deck/anim.py --- PPTX 原生动画时间轴引擎

> 让 python-pptx 生成的 PPT **在 PowerPoint / WPS 里真的会播放动画**。
> python-pptx 1.0.2 没有任何动画 API，本模块直接生成 ECMA-376 的 `<p:timing>` 与
> `<p:transition>` OOXML，写回 slide XML。

负责人：animator ・ 目标：PowerPoint 2016+/365，WPS 尽量兼容 ・ 状态：已在 PowerPoint 16 (Build 17932) 实测通过

---

## 1. 三个最关键的实测结论（先看这个）

这三点都是**用 PowerPoint COM 生成参考文件、解压对比 XML** 得到的，不是查文档猜的。踩错任何一条都会导致"文件能打开但动画不对"。

### 1.1 `grpId` 必须按 shape 各自递增

PowerPoint 给**同一个 shape 的多个整形状动画**分配 `grpId="0"`、`"1"`、`"2"`（每个 shape 各自从 0 数），
并在 `<p:bldLst>` 里为每个 `(spid, grpId)` 组合各写一条 `<p:bldP>`。

> 如果所有效果都写 `grpId="0"`，PowerPoint 会把同一 shape 的第 2、3 个动画**当成重复项静默丢弃**
> （文件不报错、不修复，只是效果变少）。这是本模块开发中最大的坑。
> 逐段文字动画（带 `p:spTgt/p:txEl/p:pRg`）反过来**必须共用 grpId=0**，靠段落区间区分。

### 1.2 强调/路径类的 `repeatCount` 与 `autoRev` 必须写在外层效果 cTn

- `repeatCount` 的单位是**千分之一**：重复 2 次写成 `repeatCount="2000"`，重复 1 次则**省略该属性**。
- `autoRev="1"`（往复）同样挂在**外层** `<p:cTn presetID=... presetClass=...>` 上。

> 把它们写到内层行为 cTn（`<p:animScale><p:cBhvr><p:cTn>`）上时，PowerPoint 仍能打开，
> 但 `Effect.Timing.Duration` 会退化成接近 0（实测 0.9s 读回 **0.0036s**）——动画瞬间跳完，看不见。

### 1.3 `p:fade` 不要带 `thruBlk`

- `<p:fade/>` = 平滑交叉淡化（COM 读回 `EntryEffect=3849`）
- `<p:fade thruBlk="1"/>` = 淡入淡出**经黑**（COM 读回 `EntryEffect=1793`），浅色 deck 上会闪黑一下

---

## 2. API

```python
from anim import Timeline, enable_show_timings, PRESETS

tl = Timeline()
tl.add(shape, "fadeUp", start=0.3, dur=0.7)     # start 是"相对本页开始的绝对秒数"
tl.add(shape2, "fade", start=0.3, dur=0.7)      # 同一 start(毫秒) -> 自动变成"与上一动画同时"
tl.transition(slide, "fade", advance=12)        # advance 秒 = 自动换片
tl.apply(slide)
```

### 2.1 `Timeline`

| 方法 | 说明 |
|---|---|
| `Timeline(*, warn_limit=True)` | 一个 slide 一个实例（也可跨页共用，见 `apply_all`） |
| `add(target, preset="fade", start=0.0, dur=0.7, *, repeat=None, slide=None, para=None)` | 加一条效果，返回 `Effect`。`target` 可以是 pptx shape 对象或 `int`(shape_id，此时需给 `slide=`) |
| `add_many(targets, preset="fadeUp", start=0.0, dur=0.6, *, stagger=0.08)` | 一组 shape 按固定步长依次入场（卡片/图标编排） |
| `add_text_build(target, preset="fadeUp", start=0.0, dur=0.5, *, stagger=0.06, paragraphs=None)` | 逐段文字动画（见第 6 节） |
| `transition(slide=None, kind="fade", dur=1.0, advance=12.0, *, click=True)` | 切页 + 自动换片；`advance=None` = 不自动换片 |
| `apply(slide)` | 写入该页的 transition + timing，返回效果条数 |
| `apply_all(slides)` | 多页批量，返回 `{index: 效果数}` |
| `total_duration()` | 本时间轴结束时间（秒，已计入 repeat） |
| `describe()` | 导出自检列表（preset/spid/para/start_ms/dur_ms/node_type），用于与 COM 对账 |
| `.warnings` | 超过 `MAX_EFFECTS_PER_SLIDE`（默认 14）时的提示 |

### 2.2 预设

全部预设都**自动播放**（外层结构固定为 `nodeType="afterEffect"/@@"withEffect"`，没有 clickEffect）。

| preset | 效果 | OOXML presetID / class / subtype | 行为 | 与 PowerPoint 原生行为一致 |
|---|---|---|---|---|
| `fade` | 淡入 | 10 / entr / 0 | set + animEffect(fade) | 是 |
| `fadeUp` | 上浮淡入 | 37 / entr / 0 | set + animEffect(fade) + anim(ppt_y +0.10→基准, decel 60000) | 是（= 原生 Rise Up） |
| `fadeDown` | 下沉淡入 | 37 / entr / 0 | 同上，ppt_y -0.10→基准 | 行为自组，动画窗格仍显示 "Rise Up" |
| `fadeLeft` | 左移淡入（从右侧进） | 37 / entr / 0 | anim(ppt_x +0.10→基准) | 同上 |
| `fadeRight` | 右移淡入（从左侧进） | 37 / entr / 0 | anim(ppt_x -0.10→基准) | 同上 |
| `zoom` | 缩放淡入 | 23 / entr / 16 | set + animEffect(fade) + animScale 86%→100% | 行为自组（比原生 0%→100% 克制） |
| `wipeUp` | 擦除（自下而上） | 22 / entr / 4 | set + animEffect(wipe(up)) | 是 |
| `wipeDown` | 擦除（自上而下） | 22 / entr / 4 | animEffect(wipe(down)) | 是 |
| `wipeLeft` / `wipeRight` | 左右擦除 | 22 / entr / 2、8 | animEffect(wipe(left/right)) | filter 决定方向 |
| `appear` | 出现（无过渡） | 1 / entr / 0 | set | 是 |
| `pulse` | 强调：放大 4% 再回弹，默认**重复 2 次** | 6 / emph / 0 | animScale by 104%，外层 `autoRev="1" repeatCount="2000"` | 是（= 原生 Grow/Shrink 的往复缩小版） |
| `grow` | 强调：放大 30% 再回弹 1 次 | 6 / emph / 0 | animScale by 130% | 是 |
| `float` | 轻微上下浮动往返，默认 2 个来回 | 35 / path / 0 | animMotion 相对路径 `M 0 0 L 0 -0.025 L 0 0`，外层 accel/decel 50000 + repeatCount | 行为自组（自定义路径） |

别名（大小写/下划线不敏感）：`fade_in`、`rise_up`、`zoom_in`、`wipe_up`、`pulsate`、`breathe` 等。

### 2.3 切换

| kind | 生成的 XML | 说明 |
|---|---|---|
| `"fade"` | `<p:transition spd advTm><p:fade/></p:transition>` | 唯一推荐值（默认） |
| `"none"` | 不写 transition | |
| `"morph"` | p14 写法 | **不要用**，见第 5 节 |

`spd` 只有 fast / med / slow 三档（ECMA 没有自定义过渡时长），由 `dur` 就近映射：
`<=0.35s → fast`，`<=0.9s → med`，否则 `slow`。
`advTm` 是**精确毫秒**，自动换片时间不受 `spd` 影响。

---

## 3. COM 实测结论（PowerPoint 16.0 / Build 17932）

测试文件：`deck/.animtest/test-1.pptx`（4 页）・完整日志：`deck/.animtest/com-report.txt`
判定标准：打开不弹修复、`MainSequence.Count` 与写入数一致、`TriggerType` 只有 2/3、`OnPageClick=0`。

```
Open OK (无修复提示). Slides.Count = 4
--- Slide 1  effects=5  EntryEffect=3849  AdvanceOnTime=-1  AdvanceTime=8s  Dur=1s
      [1] AccentBar        ET=22 TriggerType=3 Dur=0.5s Repeat=1 AutoRev=0
      [2] Title            ET=34 TriggerType=3 Dur=0.7s Repeat=1 AutoRev=0
      [3] Subtitle         ET=10 TriggerType=3 Dur=0.6s Repeat=1 AutoRev=0
      [4] Badge            ET=23 TriggerType=3 Dur=0.5s Repeat=1 AutoRev=0
      [5] Badge            ET=59 TriggerType=3 Dur=0.9s Repeat=2 AutoRev=-1
--- Slide 2  effects=8  ...  AdvanceTime=9s
--- Slide 3  effects=5  ...  AdvanceTime=10s      (含 3 个逐段效果，同属 BodyText)
--- Slide 4  effects=10 ...  AdvanceTime=12s
TOTAL effects = 28
TriggerType 汇总 (1=OnPageClick, 2=WithPrevious, 3=AfterPrevious):
    TriggerType 3 -> 28 个
OnPageClick 数量 = 0 (必须为 0 => 全部自动播放)
POWERPNT exited cleanly (no leftover)
```

读法：

- `AdvanceOnTime=-1` 是 COM 里 `msoTrue` 的表示，即**自动换片已开启**；`AdvanceTime=8/9/10/12` 秒与传入的 `advance` 完全一致。
- `EntryEffect=3849` = 平滑淡化（对应无 `thruBlk` 的 `<p:fade/>`）。
- 28 个效果 `TriggerType` 全是 3（上一动画之后），配合各页 `advTm` => 整份 deck 可无人值守连播。
- `ET`（EffectType）对照：10=Fade、34=Rise Up(fadeUp)、22=Wipe、23=Zoom、1=Appear、59=Grow/Shrink(pulse,grow)、120=自定义路径(float)。
- 强调/路径类**真实时长正确**：pulse 读回 `Dur=0.9s Repeat=2 AutoRev=-1`，grow `0.8s`，float `1.6s Repeat=2`。

另外用 LibreOffice Kit 渲染 test-1.pptx 的 4 页 PNG 全部成功（`missingFonts: []`），
证明写入 timing/transition 后**页面本身仍可正常解析与渲染**，产物在 `deck/.animtest/render/`。

---

## 4. 逐段文字动画（add_text_build）

- 每个段落一条效果，`<p:spTgt spid><p:txEl><p:pRg st="i" end="i"/></p:txEl></p:spTgt>` 精确指向段落；
- `bldLst` 里该 shape 记 `<p:bldP spid grpId="0" build="allAtOnce"/>`，多个段落效果共用 `grpId="0"`；
- 实测 slide 3 的 3 个 `BodyText` 效果全部被 PowerPoint 识别（count=5 含 3 个逐段），说明结构正确。

**不做逐字（by word/letter）**：需要 `<p:iterate>`，在部分 WPS 版本上会导致整段文字直接出现（不回退到逐字），
收益低风险高，故只提供逐段。若确实要逐字，请在 anim.py 之外单独实验并配 PowerPoint 版本门槛。

---

## 5. morph 切换：结论是"不可用"，只用 fade

任务要求尝试 `p14:morph`，实测**失败**，因此最终实现只保留 fade。证据（都是让 PowerPoint 重存后对比它写出的 XML）：

| 尝试 | 写法 | PowerPoint 行为 |
|---|---|---|
| 1 | `mc:Choice Requires="p14"` + `<p14:morph option="2"/>` + Fallback `<p:fade/>` | 能打开，但重存时 **`<p14:morph>` 被直接删掉**，Choice 里只剩空的 `<p:transition>`；COM 读 `EntryEffect=0`（等于"无切换"） |
| 2 | `Requires="p15"` + `<p15:morph>` | 同样被删，`EntryEffect=0`，`Duration` 回落到默认 1s |
| 3 | `Requires="p159"` + `<p159:morph>` | **`Presentations.Open` 直接抛 HRESULT 异常**（文件无法打开） |

结论：

1. morph 在 OOXML 里的真实归属与本机 PowerPoint 的可接受范围不匹配，硬写只会得到"无切换"甚至**打不开**；
2. morph 本身也不在 PowerPoint 2016 支持范围，WPS 更不确定；
3. 宣传片的目标是"任何机器上都能自动播放"，因此 **`kind` 只保留 fade** 是最优解。

`anim.py` 仍保留 `kind="morph"` 分支（生成 p14 写法）供实验，但**不要在生产 deck 里使用**；
`build_deck.py` 全部使用 `TRANSITION("fade", ...)`，这是正确的。

---

## 6. 在 build_deck.py 里怎么调用

Lead 的 `build_deck.py` 已经这样集成（一个薄封装 + 每页一个 Timeline）：

```python
import anim as ANIM

# 每页收集：effect 列表 + transition 记录
def emit(slide, effects, transition):
    tl = ANIM.Timeline()
    for e in effects:
        tl.add(e["shape"], preset=e["preset"], start=e["start"], dur=e["dur"])
    tl.transition(slide, **transition)      # {"kind": "fade", "dur": 1.0, "advance": 12.0}
    tl.apply(slide)

# 整份 deck 收尾（可选，兜底"使用计时"）
ANIM.enable_show_timings(prs)
```

新增页面时的推荐节奏（苹果风格，单页 6~12 个效果）：

```python
tl = ANIM.Timeline()
tl.add(title,  "fadeUp", start=0.20, dur=0.70)          # 标题
tl.add(sub,    "fade",   start=0.55, dur=0.60)          # 副标题
tl.add_many(cards, "fadeUp", start=0.90, dur=0.55, stagger=0.12)   # 卡片错峰
tl.add(badge,  "pulse",  start=2.20, dur=0.80)          # 强调（默认重复 2 次）
tl.add(dot,    "float",  start=1.60, dur=1.60)          # 轻微浮动
tl.transition(slide, "fade", dur=1.0, advance=10)       # 自动换片 10s
tl.apply(slide)
```

`advance` 建议 >= 本页 `tl.total_duration() + 2s`，否则动画还没放完就切页了。

---

## 7. 自测 / 复验

```powershell
# 1) 生成测试 deck（4 页，覆盖全部预设 + 自动换片 + 切换）
& "<python>" deck/anim_test.py --morph

# 2) PowerPoint COM 权威校验（每页效果数 / TriggerType / 切换 / 是否残留进程）
& "deck/.animtest/verify_com.ps1"

# 3) LibreOffice 渲染成 PNG（确认页面能正常打开）
& "<node>" "<libreoffice-kit cli.js>" render --input deck/.animtest/test-1.pptx --output-dir deck/.animtest/render
```

---

## 8. 已知限制 / 注意事项

1. **自动换片依赖"使用计时"**：`advTm` 生效的前提是放映时勾选了"使用计时"（PowerPoint 默认开启）。
   `enable_show_timings(prs)` 会对 `ppt/presProps.xml` 显式设 `useTimings="1"` 兜底，失败也不抛异常。
2. **过渡时长只有三档**：`spd` 仅有 fast/med/slow，`dur` 会被就近取整；换片间隔 `advTm` 是精确毫秒。
3. **fadeDown / fadeLeft / fadeRight / zoom / float 的动画窗格标签**可能显示为最近的原生预设名
   （例如 "Rise Up"），因为 presetID 只是给 UI 看的元数据，**实际渲染由行为 XML 决定**，视觉与命名一致。
4. **单页效果数**：`MAX_EFFECTS_PER_SLIDE=14` 只是软上限，超了只在 `tl.warnings` 里提示。
   10 页 208 个效果（平均 21/页）在 PowerPoint 里能正常打开，但首帧加载会慢一些。
5. **对象名唯一性**：`Shape.Name` 重复不影响动画（动画按 `spid` 定位），但为了 COM 排查方便建议保持唯一。
6. **不要直接改 build_deck.py**：本模块只提供 API，集成由 Lead 负责。
7. 同一 shape 既要有整形状动画又要有逐段动画时，整形状动画的 grpId 从 1 起（0 留给逐段构建），已自动处理。

---

## 9. 证据文件

| 文件 | 内容 |
|---|---|
| `.animtest/test-1.pptx` | 4 页自测 deck（28 个效果） |
| `.animtest/test-morph.pptx` | morph 负结论证据（EntryEffect=0） |
| `.animtest/com-report.txt` | COM 全量实测输出 |
| `.animtest/verify_com.ps1` | COM 校验脚本 |
| `.animtest/render/page-*.png` | LibreOffice 渲染结果（4 页） |
| `.animtest/_ref/enum-report.txt` | COM 遍历 117 个动画预设得到的 presetID/class/subtype/行为 权威表 |
| `.animtest/_ref/_emph2-dump.txt` | repeatCount / autoRev 挂在外层 cTn 的原始证据 |
| `.animtest/_ref/_multi-pp.pptx` | 同 shape 多动画的 grpId 递增原始证据 |
