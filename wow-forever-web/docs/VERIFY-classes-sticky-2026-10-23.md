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

## 一条没做完的，记在这里别丢

**这次没加上"防它再错位"的门禁断言。** 我写了那段判据，但它在门禁里跑不起来：
`test_classes` 跑到这里时页面已经被前面几条断言切到 `classes.html?c=not_a_class` 那一发，
换 hash 不重读文档、`reload()` 又会被跳转桩打回首页，几种导航方式都量不到 `.chgs`。
判据本身是对的（就是上面那三个数），**是测试脚手架的页面状态没接好**。
当时为了不把门禁留成红的，我把那段撤了——**撤的是断言，不是修复**。
要补的人注意：得先让 `test_classes` 在这一发上拿到一个干净的应用文档（比如先 `about:blank`
再走 `APP_BASE + "/#/classes?c=shaman"`，或给这一段单开一个 page），别复用被前面点脏的那个。
