# 职业页「技能变化」表头错位——修复与验证（2026-10-23）

## 站主报的现象

`http://127.0.0.1:8821/classes.html?c=shaman#/classes` 技能变化那一列，滚动时
「名称 / 类别 / 哪一系」那一行固定在上面，**应该固定在「新增」标题下面**，看着错位。
截图上那一行浮在列表中间，还压住一行内容。

## 真实原因：sticky 的参照物不是视口

`src/css/app.css:1455` 把这一列做成了**独立滚动框**：

```css
.chgs{max-height:72vh;overflow-y:auto;padding-right:2px}
.chgs .lgrp{top:0}
```

所以组带（「新增 17 条」那一条）是**相对 `.chgs` 框顶**吸的，正确。
但表头走的是通用那条 `src/css/board.css:29`：

```css
.board thead th { … position:sticky; top:var(--hd-h); z-index:3 }
```

`--hd-h` 是**导航高度**（app.js 实测写回，这台是 110px），那是给"表头相对视口吸顶"的页面用的。
放进 `.chgs` 这个滚动框里，它的意思就变成"离框顶 110px 处吸住"——
**正好落在列表中间，上面空出一条，还压住一行**。这就是拍到的样子。

## 改法

只在新站层加三条（`src/css/board.css`，旧站不加载这个文件，共享的 app.css 一行没动）：

```css
.chgs { --lgrp-h: 28px }
.chgs .lgrp { min-height: var(--lgrp-h) }
.chgs .board > thead > tr > th { top: var(--lgrp-h) }
```

组带高度声明成变量并钉住 `min-height`，**不去抄一次测量值**——抄来的数会随字号和内边距漂，
漂了就又回到今天这个错位。

## 验证（真浏览器量的，不是看 CSS 写的对就算）

滚动到 `.chgs.scrollTop = 340` 之后：

| 量 | 值 | 该是多少 |
| --- | --- | --- |
| 组带顶 − 滚动框顶 | **0** | 0（贴框顶） |
| 表头顶 − 组带顶 | **28** | 等于组带高 28 |
| 表头是否落在"框顶 + 导航高 110px"那个错位置 | 否（差 82px） | 否 |

实拍：`docs/screenshots/check-2026-10-23/classes-chgs-sticky.png`
（组带在上、表头紧贴其下、下面第一行完整可见）。
`site-check.py --app --only classes` **25/25 通过**。

## 防它再错位的断言：补上了（同日第二轮）

上一节记的那条欠账已经还。当时量不到 `.chgs` 的原因是**复用了被前面断言点脏的那个 page**——
`test_classes` 跑到那里时文档已经在 `classes.html?c=not_a_class` 那一发上，换 hash 不重读文档、
`reload()` 又被跳转桩打回首页。

补法是**不塞进 `test_classes`，单开一节**：`site-check.py` 的 `classes_sticky`（打印 `[6i]`），
每发自己 `browser.new_context()` + 新 page + `goto(APP_BASE + "/#/classes")`，
先 `box.scrollTop = 220` 再量（不滚进视口量到的是没吸住时的位置）。桌面四条：

| 判据 | 实测 |
| --- | --- |
| `.chgs` 是自己滚的框，且真的滚动了 | `scrollable true / scrollTop 220 / 95 行` |
| 组带 `position:sticky` 且贴框顶 | 距框顶 **0px** |
| 表头偏移 = 组带高，且 <60px（钉住"不许再抄 110"） | 表头距框顶 **28px** / 组带高 28px / `top:28px` |
| 遮挡用命中测试判：表头下沿 +2px 打到数据行、表头中点打到的还是表头 | `{underRow:true, overTh:true}` |

375 另两条是钉**相反**的行为：窄屏下 `.boardwrap` 成了横向滚动容器，sticky 参照物又换一次，
所以那一边表头与组带**故意都是 `position:static`**（board.css 与 app.css 各有一条把它关掉，
留着声明会在表顶画一条空带）。谁要重新打开，这两条会先红——这是有意的。

`python3 tools/site-check.py --app --only classes_sticky` **7/7 通过**；
实拍 `app-classes-chgs-sticky.png` 与 `app-classes-chgs-sticky-m.png`（同一目录）。

