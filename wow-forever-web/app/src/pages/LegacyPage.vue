<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="L">
    <!-- ① 主卡。2026-10-23 改口径：点数是账号通用的，但**每个角色各自分配、各自点自己的三棵树**，
         原来那句"（账号级，不随角色重置）"把两件事说反了（策划那份也点了这一条）。
         数字一律从数据现取，一个都不写死。 -->
    <div class="card lge-head">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">传承专长与传承挑战</h1>
      </div>
      <p class="dim lge-lead">完成传承挑战攒传承点数。<b>点数是账号通用的</b>，但<b>每个角色各自分配</b>：
        同一个账号下的每个角色都能用这些点数，各自点自己那三棵树，换个角色要从头点。
        常规挑战 <b class="mono">{{ nRegular }}</b> 项、每完成一项给 <b class="mono">{{ perPoint }}</b> 点；
        每个角色最多花 <b class="mono">{{ cap }}</b> 点。{{ rules.unlock || '' }}</p>
      <div class="lge-read">
        <span v-for="r in readout" :key="r.k"><b class="mono">{{ r.v }}</b>{{ r.k }}</span>
      </div>
      <div class="lge-tabs" role="tablist" aria-label="三棵传承树">
        <button v-for="(t, i) in trees" :key="t.id" type="button" role="tab" data-tg
                :data-t="t.id" :aria-selected="tree === t.id ? 'true' : 'false'"
                class="lge-tab" :class="['t' + i, { on: tree === t.id }]" @click="pickTree(t.id)">
          <b>{{ t.nameCn }}</b>
          <span class="mono">{{ knownOf(t) }} 格</span>
          <span v-if="unkOf(t)" class="mono dim">· 未公开 {{ unkOf(t) }}</span>
        </button>
      </div>
      <nav class="lge-anchor" aria-label="本页三段">
        <a v-for="a in ANCHORS" :key="a[0]" :href="hrefOf('legacy.html#' + a[0])"
           @click.prevent="goAnchor(a[0])">{{ a[1] }}</a>
      </nav>
    </div>

    <!-- ② 奖励轨：按**勾选的常规挑战点数**算进度。特殊那条不并进分母（数据里 special 标着）。 -->
    <div class="card lge-track" id="lgr">
      <div class="bhead">
        <h2 class="bt">攒到一定点数给的奖励 · {{ track.length }} 档</h2>
        <span class="bn">按你勾上的常规挑战算：已攒 <b class="mono">{{ gotPoints }}</b> 点<template
          v-if="specialPoints">（另有一条测试参与记录给 {{ specialPoints }} 点，不并进这条轨）</template></span>
      </div>
      <div class="lgr-rail">
        <div v-for="x in track" :key="x.itemId" class="lgr-i" :class="{ got: x.reached }">
          <span class="lgr-at mono">{{ x.at }} 点</span>
          <IconCell :icon-key="x.iconKey || ''" :seed="x.itemId" :cn="x.nameCn" />
          <b class="lgr-nm">{{ x.nameCn }}</b>
          <span class="lgr-st dim">{{ x.reached ? '已够' : '还差 ' + x.left + ' 点' }}</span>
        </div>
      </div>
      <p class="note">这一条轨跟着下面的勾选走。勾算是你手动标的，<b>本站不读取游戏账号</b>，
        记录只存在你这台设备的浏览器里。</p>
    </div>

    <!-- ③ 三树加点规划器。格子仍按客户端坐标摆，但**全空的排与列收掉**（2026-10-23 客户端
         把树排成 5×5，第 4 排与第 4 列整条是空的）；收掉不重排号，排号与详情里的坐标
         都用客户端真实行列，玩家看到的和客户端是同一张图。 -->
    <div class="ltreewrap">
      <div class="card ltreecard" id="ltree">
        <template v-if="curTree">
          <div class="bhead lge-planbar">
            <h2 class="bt">{{ curTree.nameCn }}<template v-if="treeAlt">（另一处叫「{{ treeAlt }}」）</template><span class="dim mono">{{ nKnown }} 个专长<template v-if="nUnk"> · {{ nUnk }} 格未公开</template></span></h2>
            <span class="bn">这一棵已投 <b class="mono">{{ treePts[tree] || 0 }}</b> 点 ·
              这个角色共 <b class="mono">{{ spent }}</b> / {{ cap }} 点 ·
              还能花 <b class="mono" :class="{ zero: left <= 0 }">{{ left }}</b> 点</span>
          </div>

          <!-- 方案条：本机多方案 + 分享链接。名字只存在浏览器里，不上传、不要登录。 -->
          <div class="lge-plans">
            <div class="lge-planlist" role="group" aria-label="本机存的方案">
              <button v-for="p in plans" :key="p.name" type="button" class="pick plan"
                      :class="{ on: p.name === activeName }" @click="usePlan(p.name)">{{ p.name }}</button>
              <span v-if="!plans.length" class="dim">还没有存过的方案</span>
            </div>
            <div class="lge-planact">
              <input v-model="planName" type="text" maxlength="16" placeholder="给这个角色的方案起个名"
                     aria-label="方案名">
              <button type="button" @click="savePlan">存为本方案</button>
              <button type="button" class="ghost" :disabled="!activeName" @click="delPlan">删除</button>
              <button type="button" class="ghost" :disabled="!spent" @click="clearThisTree">清空这一棵</button>
              <button type="button" class="ghost" :disabled="!spent" @click="clearAll">全部清空</button>
              <button type="button" @click="sharePlan">复制方案链接</button>
            </div>
          </div>

          <p class="note lge-assume">规划按<b>每层 1 点</b>估算，游戏内每一层实际要几点还没核实；
            门槛与前置照客户端给出的记录判，没进游戏逐格点过。</p>

          <div v-if="shareWarn.length" class="card lge-warn">
            <b>这条链接里的方案与当前数据对不上，已按能认的部分还原：</b>
            <ul><li v-for="(w, i) in shareWarn" :key="i">{{ w }}</li></ul>
            <button type="button" @click="dismissShare">清掉这份，从空白开始点</button>
          </div>

          <div class="lge-grid" id="lgrid" :style="{ '--cols': vis.cols.length }">
            <svg class="lge-links" aria-hidden="true" :width="box.w || 0" :height="box.h || 0"
                 :viewBox="'0 0 ' + (box.w || 1) + ' ' + (box.h || 1)">
              <line v-for="(l, i) in segs" :key="i" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2"
                    :class="{ on: l.on }" />
            </svg>
            <div v-for="r in gridRows" :key="r.row" class="lge-rowwrap">
              <span class="lge-rail mono">第{{ r.row + 1 }}排</span>
              <!-- :key="tree" 让换树时这一排格子重挂一次，好把已有的 lgeFade 入场重放一遍。
                   原来这个动画只认"元素进 DOM"，而换树走的是同一批格子就地更新，
                   所以点了标签画面其实不动——这一句才是把切换动效接上，不是新增长动画。 -->
              <div class="lge-cells" :key="tree">
                <template v-for="cell in r.cells" :key="cell.k">
                  <div v-if="cell.s.empty" class="lslot none" aria-hidden="true"></div>
                  <div v-else-if="cell.s.unknown" class="lslot unk" :data-node="cell.s.perk">
                    <b>?</b><span class="dim">未公开</span>
                  </div>
                  <button v-else-if="perkOf(cell)" type="button" class="lslot"
                          :class="[{ on: open === perkOf(cell).id, lock: !canAddHere(perkOf(cell).id).ok },
                                   { filled: rankOf(perkOf(cell).id) > 0 }]"
                          :data-perk="perkOf(cell).id" :data-node="perkOf(cell).id"
                          :aria-pressed="open === perkOf(cell).id ? 'true' : 'false'"
                          @click="toggle(perkOf(cell).id)">
                    <span class="lcell">
                      <span class="ico-wrap">
                        <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
                          <rect width="28" height="28" rx="4" :fill="tileOf(cell).fill" :stroke="tileOf(cell).stroke" />
                          <text x="14" y="19" text-anchor="middle" font-size="12" :fill="tileOf(cell).text"
                                font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ tileOf(cell).letter }}</text>
                        </svg>
                        <img v-if="perkOf(cell).iconKey && !broken[perkOf(cell).id]" class="ico"
                             :src="iconUrl(perkOf(cell).iconKey)" alt="" loading="lazy"
                             @error="broken[perkOf(cell).id] = true">
                      </span>
                      <span class="rk mono"><b v-if="rankOf(perkOf(cell).id)" class="now">{{ rankOf(perkOf(cell).id) }}</b>{{ rankOf(perkOf(cell).id) ? '/' : '' }}{{ perkOf(cell).maxRank == null ? '?' : perkOf(cell).maxRank }} 层</span>
                      <em v-if="perkOf(cell).prerequisiteCn" class="lge-tag">有前置</em>
                    </span>
                    <span class="nm">{{ perkOf(cell).nameCn }}</span>
                    <em v-if="perkOf(cell).treePointsRequired" class="lge-gate mono">要 {{ perkOf(cell).treePointsRequired }} 点</em>
                  </button>
                  <div v-else class="lslot unk"><b>?</b></div>
                </template>
              </div>
            </div>
          </div>
          <ul class="lge-legend">
            <li><i class="lg lg-perk"></i>这一格有专长，点它选中，再用下面的 ＋ / － 加点</li>
            <li><i class="lg lg-gate"></i>写着「要 N 点」的格子，要先在这一棵投满 N 点才点得开</li>
            <li><i class="lg lg-line"></i>格子之间的线是前置关系（客户端给的）</li>
            <li><i class="lg lg-unk"></i>有这一格，内容还没公开</li>
          </ul>
        </template>
        <div v-else class="empty">这棵树还没收录。</div>
      </div>

      <!-- 详情栏：没选的时候说这一棵树，选了说这个专长 + 明确的加减按钮 -->
      <div id="ldet">
        <div v-if="!openPerk" class="card ldetail">
          <h2>{{ curTree ? curTree.nameCn + '这一棵' : '三棵传承树' }}</h2>
          <div class="lge-read">
            <span v-for="r in treeReadout" :key="r.k"><b class="mono">{{ r.v }}</b>{{ r.k }}</span>
          </div>
          <p class="note">先点一个格子，这里会出现「＋ 加一点 / － 退一点」和点不开的原因。</p>
        </div>
        <div v-else class="card ldetail lge-perk">
          <div class="lge-prow">
            <span class="lge-pico">
              <svg viewBox="0 0 28 28" width="52" height="52" aria-hidden="true">
                <rect width="28" height="28" rx="4" :fill="tileOf2.fill" :stroke="tileOf2.stroke" />
                <text x="14" y="19" text-anchor="middle" font-size="12" :fill="tileOf2.text"
                      font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ tileOf2.letter }}</text>
              </svg>
              <img v-if="openPerk.iconKey && !broken['d' + openPerk.id]" class="ico"
                   :src="iconUrl(openPerk.iconKey)" alt="" loading="lazy"
                   @error="broken['d' + openPerk.id] = true">
            </span>
            <div class="lge-ptitle">
              <h2>{{ openPerk.nameCn }}</h2>
              <div class="lge-ranks">
                <i v-for="k in rankDots" :key="k" class="rd" :class="{ lit: k <= rankNow }"></i>
                <span class="mono">{{ maxRankTxt }}</span>
                <span class="mono dim">已点 {{ rankNow }} 点</span>
              </div>
            </div>
          </div>
          <div class="lmeta">
            <span>属于：<b>{{ openPerk.treeCn }}</b></span>
            <span>位置：第 {{ openPerk.row + 1 }} 排第 {{ openPerk.col + 1 }} 列</span>
            <span v-if="openPerk.treePointsRequired != null">本树门槛：<b>{{ openPerk.treePointsRequired }}</b> 点
              <span class="dim">（这一棵现在投了 {{ treePts[openPerk.treeId] || 0 }} 点）</span></span>
            <span>前置：<button v-if="prereqPerk" type="button" class="lge-jump" data-jump
                                @click="selectPerk(prereqPerk.id)">{{ openPerk.prerequisiteCn }}</button>
              <b v-else-if="openPerk.prerequisiteCn">{{ openPerk.prerequisiteCn }}</b>
              <span v-else class="dim">没有前置</span></span>
            <span class="lge-eff">具体效果待实测（本站不存别人转述的逐级说明）</span>
          </div>
          <div class="lge-act">
            <button type="button" data-act="add" :disabled="!addOk.ok" @click="act('add')">＋ 加一点</button>
            <button type="button" data-act="sub" :disabled="rankNow <= 0" @click="act('sub')">－ 退一点</button>
          </div>
          <p class="note" v-if="!addOk.ok">{{ addOk.reason }}</p>
          <p class="note dim" v-else-if="rankNow >= (openPerk.maxRank || 0)">这一格已经点满了。</p>
        </div>
      </div>
    </div>

    <!-- ④ 常规挑战：六组，每条一个手动勾选框 -->
    <div class="card">
      <h2>传承挑战 · 常规 {{ nRegular }} 项</h2>
      <p class="dim">每完成一项给 {{ perPoint }} 点。勾算是你手动标的，只存在本机浏览器里。</p>
      <div class="field">
        <input v-model="q" type="search" placeholder="搜挑战名、完成条件或归属">
        <span class="dim mono">{{ shownChallenges }} / {{ nRegular }} 项 · 已勾 {{ doneRegular }} 项</span>
      </div>
    </div>

    <div id="lch">
      <template v-for="blk in challengeBlocks" :key="blk.c.id">
        <div class="card lchgrp" :class="{ closed: !isOn(blk.c.id) }">
          <button type="button" class="lchhead" data-blk :data-b="blk.c.id"
                  :aria-expanded="isOn(blk.c.id) ? 'true' : 'false'" @click="toggleBlock(blk.c.id)">
            <b>{{ blk.c.nameCn }}</b>
            <span class="dim mono">{{ blk.rows.length }}<template v-if="blk.rows.length !== blk.c.items.length"> / {{ blk.c.items.length }}</template> 项 · 已勾 {{ blk.done }} · 合计 {{ blk.sum }} 点</span>
            <i class="lchcaret" aria-hidden="true"></i>
          </button>
          <!-- 折叠：外层在展开这一刻变成"只有一行、行高从 0 长满"的容器（motion.css 的 unfold），
               所以子内容要有一个单独的包裹层。原来这里挂的是 animation，但元素是 v-show，
               只有页面加载那一次会播——折叠与展开其实一动不动，这轮才是真的接上。 -->
          <Transition name="unfold">
            <div v-show="isOn(blk.c.id)" class="lchbody"><div class="wf-in">
            <div v-if="(blk.c.subcategories || []).length" class="chips">
              <template v-for="s in blk.c.subcategories" :key="s">
                <span v-if="chipCount(blk.c, s)" class="chipc">{{ s }}<b class="mono">{{ chipCount(blk.c, s) }}</b></span>
              </template>
            </div>
            <!-- 摆得成矩阵的组（职业 9×3、商业技能 6×3）用网格：一屏看完这一组勾了哪些。
                 列头是数据里剥出来的档位，格子里只放勾，完成条件走 title 与下面那行读数。 -->
            <div v-if="blk.matrix" class="lmtxwrap">
              <table class="lmtx">
                <thead>
                  <tr><th class="lmtxsub"><span class="sr">归属</span></th>
                    <th v-for="col in blk.matrix.cols" :key="col" scope="col">{{ col }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="r in blk.matrix.rows" :key="r.sub">
                    <th scope="row" class="lmtxsub">{{ r.sub }}</th>
                    <td v-for="(cell, ci) in r.cells" :key="ci"
                        :class="{ done: checks[cell.item.id] }">
                      <label class="lchk lmtxcell"
                             :title="cell.item.nameCn + '：' + (cell.item.requirement || '完成条件未记录')">
                        <input type="checkbox" :checked="!!checks[cell.item.id]" data-chk
                               :id="'chk' + cell.item.id" @change="toggleCheck(cell.item.id); picked = cell.item"
                               :aria-label="'标记完成：' + cell.item.nameCn">
                      </label>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p class="dim lmtxread">
                <template v-if="picked">刚动的这条：<b>{{ picked.nameCn }}</b>
                  —— {{ picked.requirement || '完成条件未记录' }}<span class="mono">（{{ picked.points == null ? '—' : picked.points }} 点）</span></template>
                <template v-else>格子里一格一条，停在上面能看完成条件；勾一下这里会写出那条是什么。</template>
              </p>
            </div>
            <div v-else class="boardwrap">
              <table class="board ltab">
                <colgroup><col class="c-chk"><col class="c-ico"><col style="width:26%"><col><col style="width:14%"><col class="c-num"></colgroup>
                <thead><tr><th class="c-chk"><span class="sr">完成</span></th><th class="c-ico">图标</th><th>挑战</th><th>完成条件</th><th>归属</th><th class="c-num">点数</th></tr></thead>
                <tbody>
                  <tr v-for="(x, i) in blk.rows" :key="x.id !== undefined ? x.id : i" :class="{ done: checks[x.id] }">
                    <td class="c-chk"><label class="lchk"><input type="checkbox" :checked="!!checks[x.id]" data-chk
                                             :id="'chk' + x.id" @change="toggleCheck(x.id); picked = x"
                                             :aria-label="'标记完成：' + x.nameCn"></label></td>
                    <td class="ich"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.nameCn" /></td>
                    <td><label :for="'chk' + x.id"><HlText :text="x.nameCn" :q="q" /></label><span class="dim mono">#{{ x.id }}</span></td>
                    <td class="dim"><HlText :text="x.requirement || '未记录'" :q="q" /></td>
                    <td class="dim">{{ x.sub || x.group || blk.c.nameCn }}</td>
                    <td class="mono">{{ x.points == null ? '—' : x.points }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            </div></div>
          </Transition>
        </div>
      </template>
      <div v-if="!shownChallenges" class="card">
        <div class="empty">这个关键词下没有挑战，换个说法试试（比如"25 级""烹饪""军衔"）。</div>
      </div>
    </div>

    <!-- ⑤ 那条测试参与记录单列：不并进常规分母，也不默认勾上 -->
    <div class="card lge-special" v-if="specialItems.length">
      <h2>另有一条不计进常规的挑战</h2>
      <div class="boardwrap">
        <table class="board ltab lge-sptab">
          <colgroup><col class="c-chk"><col class="c-ico"><col style="width:30%"><col><col class="c-num"></colgroup>
          <tbody>
            <tr v-for="x in specialItems" :key="x.id" :class="{ done: checks[x.id] }">
              <td class="c-chk"><label class="lchk"><input type="checkbox" :checked="!!checks[x.id]" data-chk
                       :id="'chk' + x.id" @change="toggleCheck(x.id)"
                       :aria-label="'标记完成：' + x.nameCn"></label></td>
              <td class="ich"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.nameCn" /></td>
              <td><label :for="'chk' + x.id">{{ x.nameCn }}</label><span class="dim mono">#{{ x.id }}</span></td>
              <td class="dim">{{ x.requirement || '未记录' }}</td>
              <td class="mono">{{ x.points }} 点</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="note">这一条是客户端里单独标了 <b>{{ specialPointsOf }}</b> 点的测试参与记录，
        官方那篇说的 {{ nRegular }} 项常规挑战里<b>没有它</b>；正式服还给不给、谁能领，本站没核实，
        所以它<b>不并进上面那条奖励轨</b>，也不默认替你勾上。</p>
    </div>

    <!-- ⑥ 常被问到的四件事（2026-10-25）。只写玩家真要判断的，句子本站自己写，
         数一律从 legacy.json 现取；开放条件那句直接引数据里官方那篇的说法，不改写。
         不做的事：洗点花费、先点什么最划算这类没核实的，一律不编（数据里 notCollected 记着）。 -->
    <div class="card lge-faq" id="lfaq">
      <h2>常被问到的四件事</h2>
      <dl class="lge-qa">
        <dt>传承点数从哪来？</dt>
        <dd>{{ rules.unlock }}常规挑战每完成一项给 <b class="mono">{{ perPoint }}</b> 点，一共
          <b class="mono">{{ nRegular }}</b> 项。</dd>
        <dt>点数是账号共用的，还是每个角色自己的？</dt>
        <dd>点数是<b>账号通用</b>的，但<b>每个角色各自分配</b>：换一个角色要从头点。
          一个角色最多能花 <b class="mono">{{ cap }}</b> 点。</dd>
        <dt>{{ nRegular }} 项全做完能拿多少点？客户端里那个 {{ cnt.challengePointSum }} 是什么？</dt>
        <dd>常规挑战全做完是 <b class="mono">{{ cnt.challengePointsRegular }}</b> 点。
          <span class="mono">{{ cnt.challengePointSum }}</span> 是 {{ cnt.challenges }} 条条目的点数合计
          （含下面那条测试参与记录），<b>不是人人可得</b>，也不是挑战条数。</dd>
        <dt v-if="specialItems.length">那条 {{ specialPointsOf }} 点的记录算不算？</dt>
        <dd v-if="specialItems.length">它是<b>{{ specialItems[0].nameCn }}</b>，官方那篇说的
          {{ nRegular }} 项常规挑战里没有它；正式服还给不给、谁能领，本站没核实，
          所以不并进上面那条奖励轨。</dd>
      </dl>
      <p class="dim">每个专长各层的具体效果，本站没有可靠文本，一律写「具体效果待实测」——不生成、不搬别人转述的说明。</p>
    </div>

    <transition name="lge-toast"><div v-if="toastMsg" class="lge-toast" role="status">{{ toastMsg }}</div></transition>
  </template>
</template>

<script setup>
/* 传承页（2026-10-23 第二轮，方案见 docs/PLAN-传承页完善-2026-10-23.md，
   数据事实见 docs/DATA-传承页更新-2026-10-23.md）。
   这一轮做的是"能用"：加点规划器（门槛/前置/上限/退点保护）、奖励进度轨、
   挑战手动勾选、本机多方案与可校验的分享链接。
   三条硬边界：① 一个事实数字都不写死，全部从 legacy.json 现取；
   ② 每层按 1 点只是规划假设，界面上固定写出来；
   ③ 没有可靠效果文本的专长一律显示"具体效果待实测"，不生成、不搬别人的逐级说明。 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { load } from '../lib/data.js';
import { tileStyle, iconUrl } from '../lib/glyph.js';
import { hrefOf } from '../lib/nav.js';
import {
  buildCtx, encode, decode, add, remove, canAdd, clearTree,
  totalSpent, spentByTree, applyChecks, challengeIndex, rewardTrack, visibleGrid, challengeMatrix
} from '../lib/legacy-plan.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';

const HEAD_ART = 'img/art/races/skyborne.webp';
const ANCHORS = [['ltree', '传承树'], ['lch', '传承挑战'], ['lgr', '进度奖励'], ['lfaq', '常见问答']];
/* 本机存储的键：与天赋计算器同一款前缀（wfs. = 本站），三件事各存一份，
   方案与个人勾选分开——分享链接只带方案，绝不带勾选记录。 */
const LS_PLANS = 'wfs.legacy.plans';
const LS_ACTIVE = 'wfs.legacy.active';
const LS_CHECKS = 'wfs.legacy.checks';

const L = ref(null);
const ctx = ref(null);
const err = ref('');
const tree = ref('');
const open = ref('');
const q = ref('');
const broken = ref({});
const expanded = ref([]);
const state = ref({});
const checks = ref({});
const plans = ref([]);
const activeName = ref('');
const planName = ref('');
const shareWarn = ref([]);
const segs = ref([]);
const box = ref({ w: 0, h: 0 });
const toastMsg = ref('');
const route = useRoute();
const router = useRouter();
let toastTimer = null;

function toast(m) {
  toastMsg.value = m;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastMsg.value = ''; }, 2600);
}
function store(key, val) {
  try {
    if (val === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, val);
    return null;
  } catch (e) {
    toast('本机存储不可用，方案与勾选只在这次浏览里有效');
    return null;
  }
}
/* 读回来的一律 try 解析：坏 JSON 当没有，不把页面搞白，也不拿坏数据去覆盖 */
function readJson(key) {
  const raw = store(key);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch (e) { return null; }
}
function writeJson(key, val) { store(key, JSON.stringify(val)); }

function boot() {
  err.value = '';
  load('data/legacy.json')
    .then((d) => {
      L.value = d;
      const c = buildCtx(d);
      ctx.value = c;
      const ts = d.trees || [];
      const qt = String(route.query.t || '');
      tree.value = ts.some((t) => t.id === qt) ? qt : ((ts[0] || {}).id || '');
      open.value = String(route.query.p || '');
      expanded.value = [(((d.challenges || [])[0] || {}).id) || ''].filter(Boolean);
      loadLocal(c);
      let qq = String(route.query.q || '');
      if (qq && !open.value) {
        const lk = qq.trim().toLowerCase();
        const hitp = (d.perks || []).filter((x) => String(x.nameCn || '').toLowerCase() === lk)[0];
        if (hitp) { open.value = hitp.id; tree.value = hitp.treeId || tree.value; qq = ''; }
      }
      q.value = qq;
      scrollTo(String(route.query.to || ''));
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);

/* ============ 本机方案与个人勾选 ============ */
function loadLocal(c) {
  const idx = challengeIndex(c);
  const savedChecks = readJson(LS_CHECKS);
  const applied = applyChecks(c, Array.isArray(savedChecks) ? savedChecks : []);
  checks.value = applied.set;
  if (applied.dropped.length) {
    writeJson(LS_CHECKS, applied.kept);
    toast('本机存着 ' + applied.dropped.length + ' 条已经不存在的挑战勾选记录，已丢掉，不会错记到别的挑战上');
  }
  const ps = readJson(LS_PLANS);
  plans.value = Array.isArray(ps) ? ps.filter((x) => x && x.name && x.code) : [];
  activeName.value = String(store(LS_ACTIVE) || '');
  const cur = plans.value.filter((x) => x.name === activeName.value)[0];
  const linkCode = String(route.query.plan || '');
  /* 链接里的方案优先于本机方案：来路不明的那份要先过校验，认不认得全都要说出来 */
  const code = linkCode || (cur ? cur.code : '');
  const dec = code ? decode(c, code) : { state: {}, errors: [] };
  state.value = dec.state;
  if (linkCode && dec.errors.length) shareWarn.value = dec.errors;
  else if (dec.errors.length) toast('本机这个方案与当前数据有点对不上，已按能认的部分还原');
  planName.value = activeName.value || '';
}
function persistPlans() { writeJson(LS_PLANS, plans.value); }
function savePlan() {
  const c = ctx.value; if (!c) return;
  const name = String(planName.value || '').trim() || ('方案 ' + (plans.value.length + 1));
  const code = encode(c, state.value);
  const hit = plans.value.filter((x) => x.name === name)[0];
  if (hit) { hit.code = code; hit.at = today(); }
  else plans.value.push({ name: name, code: code, at: today() });
  activeName.value = name;
  store(LS_ACTIVE, name);
  persistPlans();
  toast('已存到本机方案「' + name + '」');
}
function usePlan(name) {
  const c = ctx.value; if (!c) return;
  const p = plans.value.filter((x) => x.name === name)[0];
  if (!p) return;
  const dec = decode(c, p.code);
  state.value = dec.state;
  activeName.value = name;
  planName.value = name;
  store(LS_ACTIVE, name);
  if (dec.errors.length) toast('这个方案与当前数据有点对不上：' + dec.errors[0]);
}
function delPlan() {
  const name = activeName.value;
  if (!name) return;
  plans.value = plans.value.filter((x) => x.name !== name);
  persistPlans();
  activeName.value = '';
  planName.value = '';
  store(LS_ACTIVE, '');
  toast('已删掉本机方案「' + name + '」（加点还在页面上，要一起清就点全部清空）');
}
function sharePlan() {
  const c = ctx.value; if (!c) return;
  /* 只带方案码：个人挑战勾选存在本机，不进链接（方案里也就没有别人的进度） */
  const code = encode(c, state.value);
  router.replace({ path: '/legacy', query: { t: tree.value, plan: code } }).then(() => {
    const url = location.href;
    const done = () => toast('方案链接已复制（只含加点方案，不含挑战勾选）');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done, () => { fallbackCopy(url); done(); });
    } else { fallbackCopy(url); done(); }
  });
}
function fallbackCopy(text) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.left = '-9999px';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
  } catch (e) { /* 复制失败已经 toast 过链接文本，不静默假装成功 */ }
}
function dismissShare() {
  shareWarn.value = [];
  state.value = {};
  router.replace({ path: '/legacy', query: { t: tree.value } });
}
function today() { return new Date().toISOString().slice(0, 10); }

/* ============ 加点 ============ */
function act(mode) {
  const c = ctx.value; const id = open.value;
  if (!c || !id) return;
  const r = mode === 'add' ? add(c, state.value, id) : remove(c, state.value, id);
  if (r.msg) toast(r.msg);
  if (r.state !== state.value) {
    state.value = r.state;
    if (activeName.value) {
      const p = plans.value.filter((x) => x.name === activeName.value)[0];
      if (p) { p.code = encode(c, r.state); p.at = today(); persistPlans(); }
    }
  }
}
function clearThisTree() {
  const c = ctx.value; if (!c) return;
  state.value = clearTree(c, state.value, tree.value);
  toast('已清空「' + ((curTree.value || {}).nameCn || '') + '」这一棵');
}
function clearAll() {
  state.value = {};
  toast('已清空全部加点');
}
function toggleCheck(id) {
  const next = Object.assign({}, checks.value);
  const k = String(id);
  if (next[k]) delete next[k]; else next[k] = true;
  checks.value = next;
  writeJson(LS_CHECKS, Object.keys(next));
}

/* ============ 派生数据 ============ */
const meta = computed(() => (L.value && L.value.meta) || {});
const rules = computed(() => meta.value.rules || {});
const cnt = computed(() => meta.value.counts || {});
const trees = computed(() => (L.value && L.value.trees) || []);
const perks = computed(() => (L.value && L.value.perks) || []);
const challenges = computed(() => (L.value && L.value.challenges) || []);
const perkById = computed(() => {
  const m = {};
  perks.value.forEach((p) => { m[p.id] = p; });
  return m;
});
const idx = computed(() => (ctx.value ? challengeIndex(ctx.value) : { items: [], regular: [], special: [], map: {} }));
const nRegular = computed(() => idx.value.regular.length);
const perPoint = computed(() => rules.value.pointPerChallenge == null ? '?' : rules.value.pointPerChallenge);
const cap = computed(() => (ctx.value && ctx.value.cap != null ? ctx.value.cap : '?'));
const spent = computed(() => totalSpent(state.value));
const left = computed(() => (typeof cap.value === 'number' ? Math.max(0, cap.value - spent.value) : 0));
const treePts = computed(() => (ctx.value ? spentByTree(ctx.value, state.value) : {}));
/* 勾选统计算一遍就好（奖励轨、页头读数、特殊记录都读它） */
const checkStat = computed(() => (ctx.value
  ? applyChecks(ctx.value, Object.keys(checks.value)) : { regularPoints: 0, regularDone: 0, specialPoints: 0 }));
const gotPoints = computed(() => checkStat.value.regularPoints);
const doneRegular = computed(() => checkStat.value.regularDone);
const specialPoints = computed(() => checkStat.value.specialPoints);
const specialItems = computed(() => idx.value.special);
const specialPointsOf = computed(() => (idx.value.special[0] || {}).points || 0);
const track = computed(() => (ctx.value ? rewardTrack(ctx.value, gotPoints.value) : []));

const readout = computed(() => [
  { v: nRegular.value, k: '项常规挑战' },
  { v: cap.value, k: '点：每个角色最多能花' },
  { v: perks.value.length, k: '个专长有明细' },
  { v: (cnt.value.unknownSlots || 0), k: '格还没公开' },
  { v: (cnt.value.rewards || 0), k: '档进度奖励' }
]);

const curTree = computed(() => trees.value.filter((t) => t.id === tree.value)[0] || null);
/* 官方繁中那篇把「资源」这棵树叫「精明」——两源分歧不裁决，标题里并排给出来 */
const treeAlt = computed(() => {
  const al = ((curTree.value || {}).nameAlt || [])[0];
  return al ? (al.nameCn || '') : '';
});
const knownOf = (t) => (t.slots || []).filter((x) => !x.empty && !x.unknown).length;
const unkOf = (t) => (t.slots || []).filter((x) => x.unknown).length;
const nKnown = computed(() => (curTree.value ? knownOf(curTree.value) : 0));
const nUnk = computed(() => (curTree.value ? unkOf(curTree.value) : 0));
const treeReadout = computed(() => {
  const t = curTree.value;
  if (!t) return [];
  const inTree = perks.value.filter((p) => p.treeId === t.id);
  const ranks = inTree.reduce((a, p) => a + (p.maxRank || 0), 0);
  const preN = inTree.filter((p) => p.prerequisiteCn).length;
  return [{ v: inTree.length, k: '个专长' }, { v: ranks, k: '层最多可点' },
    { v: preN, k: '个要先点前置' }];
});

/* 显示用的网格：全空的排/列收掉，但排号与详情里的坐标仍用客户端真实值 */
const vis = computed(() => (curTree.value ? visibleGrid(curTree.value) : { rows: [], cols: [] }));
const gridRows = computed(() => {
  const t = curTree.value;
  const out = [];
  if (!t) return out;
  vis.value.rows.forEach((row) => {
    const cells = [];
    vis.value.cols.forEach((col) => {
      const s = t.slots.filter((x) => x.row === row && x.col === col)[0] || { empty: true };
      cells.push({ k: row + '-' + col, s: s });
    });
    out.push({ row: row, cells: cells });
  });
  return out;
});

const openPerk = computed(() => perkById.value[open.value] || null);
const prereqPerk = computed(() => {
  const p = openPerk.value;
  if (!p || !p.prerequisite) return null;
  return perkById.value[p.prerequisite] || null;
});
const rankNow = computed(() => Number(state.value[open.value]) || 0);
const maxRankTxt = computed(() => {
  const p = openPerk.value;
  if (!p) return '';
  return p.maxRank == null ? '层数未核实' : '最多 ' + p.maxRank + ' 层';
});
const rankDots = computed(() => {
  const p = openPerk.value;
  return p && p.maxRank != null ? Math.min(p.maxRank, 8) : 0;
});
const addOk = computed(() => (openPerk.value ? canAdd(ctx.value, state.value, openPerk.value.id) : { ok: false, reason: '' }));
function canAddHere(id) { return ctx.value ? canAdd(ctx.value, state.value, id) : { ok: false, reason: '' }; }
function rankOf(id) { return Number(state.value[id]) || 0; }

function perkOf(cell) { return perkById.value[cell.s.perk] || null; }
function toggle(id) { open.value = open.value === id ? '' : id; }
function selectPerk(id) {
  const p = perkById.value[id];
  if (!p) return;
  tree.value = p.treeId || tree.value;
  open.value = id;
}
function pickTree(id) {
  tree.value = id;
  const p = perkById.value[open.value];
  if (p && p.treeId !== id) open.value = '';
}
function tileOf(cell) { const p = perkOf(cell); return tileStyle(p.id, p.nameCn); }
const tileOf2 = computed(() => {
  const p = openPerk.value;
  return p ? tileStyle(p.id, p.nameCn) : { fill: '', stroke: '', text: '', letter: '' };
});

/* ============ 前置连线：渲染完量格子位置再画（与天赋计算器同一套做法） ============ */
function drawLinks() {
  const el = document.getElementById('lgrid');
  if (!el || !curTree.value) { segs.value = []; return; }
  const b = el.getBoundingClientRect();
  box.value = { w: Math.round(b.width), h: Math.round(b.height) };
  const pos = {};
  el.querySelectorAll('[data-node]').forEach((n) => { pos[n.getAttribute('data-node')] = n; });
  const arr = [];
  (curTree.value.links || []).forEach((l) => {
    const a = pos[l.from], z = pos[l.to];
    if (!a || !z) return;
    const ra = a.getBoundingClientRect(), rz = z.getBoundingClientRect();
    arr.push({
      x1: +(ra.left - b.left + ra.width / 2).toFixed(1), y1: +(ra.top - b.top + ra.height / 2).toFixed(1),
      x2: +(rz.left - b.left + rz.width / 2).toFixed(1), y2: +(rz.top - b.top + rz.height / 2).toFixed(1),
      on: (rankOf(l.from) > 0) && (rankOf(l.to) > 0)
    });
  });
  segs.value = arr;
}
/* 已经停在传承页时又点开一条分享链接（地址栏只换了 query）：组件不会重建，
   boot() 也不再跑，方案就得手动刷新才生效——所以这里单独接住 plan 的变化。 */
watch(() => route.query.plan, (v) => {
  const c = ctx.value;
  if (!c || v === undefined) return;
  const code = String(v || '');
  if (!code) { shareWarn.value = []; return; }
  const dec = decode(c, code);
  state.value = dec.state;
  shareWarn.value = dec.errors;
});
watch([tree, state, open], () => { nextTick(drawLinks); }, { deep: true });
onMounted(() => {
  nextTick(drawLinks);
  window.addEventListener('resize', drawLinks);
});
onBeforeUnmount(() => { window.removeEventListener('resize', drawLinks); if (toastTimer) clearTimeout(toastTimer); });

/* ============ 挑战筛选与折叠 ============ */
const kw = computed(() => q.value.trim().toLowerCase());
/* 六组里只摆常规条目：那条测试参与记录在下面的单列卡里，不混进分组计数 */
const groups = computed(() => challenges.value.map((g) =>
  Object.assign({}, g, { items: (g.items || []).filter((x) => !x.special) })));
function rowsOf(c) {
  const k = kw.value;
  if (!k) return c.items || [];
  return (c.items || []).filter((x) => (((x.nameCn || '') + ' ' + (x.requirement || '') + ' ' +
    (x.sub || '') + ' ' + (x.group || ''))).toLowerCase().indexOf(k) >= 0);
}
const challengeBlocks = computed(() => groups.value.map((c) => {
  const rows = rowsOf(c);
  return {
    c: c, rows: rows,
    sum: rows.reduce((a, x) => a + (x.points || 0), 0),
    done: rows.filter((x) => checks.value[x.id]).length,
    /* 搜索态一律回表格：搜索要的是命中行连着完成条件一起看，网格会把条件藏起来。
       摆不摆得成矩阵由数据决定（档数齐不齐、列头剥不剥得出来），不在这里写死哪几组。 */
    matrix: kw.value ? null : challengeMatrix(c.items)
  };
}).filter((b) => b.rows.length));
/* 勾一格就把那一格是什么写出来：矩阵里只放得下一个勾，完成条件得有个地方落地。 */
const picked = ref(null);
const shownChallenges = computed(() => challengeBlocks.value.reduce((a, b) => a + b.rows.length, 0));
function chipCount(c, s) { return (c.items || []).filter((x) => x.sub === s || x.group === s).length; }
function isOn(id) { return kw.value ? true : expanded.value.indexOf(id) >= 0; }
function toggleBlock(id) {
  const i = expanded.value.indexOf(id);
  if (i >= 0) expanded.value.splice(i, 1); else expanded.value.push(id);
}

/* ============ 页内锚点（哈希路由里不能写裸 #id） ============ */
function scrollTo(id) {
  if (!id) return;
  nextTick(() => {
    const el = document.getElementById(id);
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
  });
}
function goAnchor(id) { scrollTo(id); }
</script>

<style scoped>
/* 规划器读数条：与板块头同一套语言，超额时"还能花"变红 */
.lge-planbar { margin-bottom: 10px }
.lge-planbar .zero { color: var(--bad) }
/* 方案条 */
.lge-plans { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center;
  padding: 9px 0; border-top: 1px solid var(--line-2); border-bottom: 1px solid var(--line-2); margin-bottom: 10px }
.lge-planlist { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; min-width: 0 }
.lge-planact { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; flex: 1 1 320px; min-width: 0 }
.lge-planact input[type=text] { flex: 1 1 170px; min-width: 0; height: 44px }
.lge-planact button { min-height: 44px }
/* 规划假设与说明：固定显示，不是悬停才看得到 */
.lge-assume { margin: 0 0 10px; font-size: 12.5px }
.lge-warn { border-color: var(--warn); margin: 0 0 10px }
.lge-warn ul { margin: 6px 0 10px; padding-left: 18px; font-size: 12.5px }
/* 网格与连线：SVG 铺在格子下面，不吃点击 */
.lge-grid { position: relative }
.lge-links { position: absolute; left: 0; top: 0; pointer-events: none; z-index: 0 }
.lge-links line { stroke: var(--line); stroke-width: 2 }
.lge-links line.on { stroke: var(--gold) }
.lge-rowwrap, .lge-cells { position: relative; z-index: 1 }
/* 格子上两枚角标各占一个角。门槛这枚**挂在整格（.lslot）的右上角**：
   挂在 .lcell 上时 .lcell 只有图标那么宽（实测 40px），"要 5 点"会被挤成两行、
   正好压在层数与名字上（1440 实拍发现）。前置那枚仍走 board.css 的 .lge-tag（左上角）。 */
.lslot { position: relative }
.lge-gate { position: absolute; right: 3px; top: 3px; white-space: nowrap;
  font-size: 9.5px; font-style: normal; line-height: 1.35; color: var(--warn);
  background: rgba(8, 10, 14, .82); border: 1px solid rgba(221, 159, 68, .45);
  padding: 0 3px; border-radius: 3px; z-index: 2 }
.lslot.lock { opacity: .58 }
.lslot.filled { border-color: var(--gold-deep) }
.lslot .rk .now { color: var(--gold); font-size: 13px }
/* 图例里两种新标记要长得像它们在格子上的样子 */
.lg-gate { background: none; border: 1px solid var(--line-2); position: relative }
.lg-gate::after { content: "5"; position: absolute; right: -3px; top: -4px; font-size: 9px; line-height: 1.2;
  color: var(--warn); background: rgba(8, 10, 14, .9); border: 1px solid rgba(221, 159, 68, .45);
  border-radius: 3px; padding: 0 2px }
.lg-line { background: none; border: 1px solid var(--line-2); position: relative }
.lg-line::after { content: ""; position: absolute; left: -6px; top: 8px; width: 30px; height: 2px;
  background: var(--gold); z-index: -1 }
/* 详情栏的加减按钮：明确的两个大按钮，不是"点格子切换"这种隐式操作 */
.lge-act { display: flex; gap: 8px; margin-top: 11px }
.lge-act button { flex: 1 1 0; min-height: 46px; font-size: 14.5px }
.lge-eff { display: block; color: var(--txt-dim); font-size: 12.5px }
.lge-ranks .rd { width: 9px; height: 9px; border-radius: 50%; border: 1px solid var(--line); display: inline-block; margin-right: 3px }
.lge-ranks .rd.lit { background: var(--gold); border-color: var(--gold) }
/* 奖励轨 */
.lgr-rail { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0 4px }
.lgr-i { flex: 1 1 150px; min-width: 0; display: flex; flex-direction: column; gap: 4px;
  border: 1px solid var(--line-2); border-radius: 6px; padding: 9px 10px; background: var(--panel-2) }
.lgr-i.got { border-color: var(--gold-deep); background: rgba(201, 162, 74, .07) }
.lgr-at { font-size: 11.5px; color: var(--txt-muted) }
.lgr-nm { font-size: 13.5px; color: var(--txt-title) }
.lgr-st { font-size: 12px }
.lgr-i.got .lgr-st { color: var(--ok) }
/* 挑战勾选：整行完成后压暗一点，勾上的行给一条金色左沿 */
.ltab tbody tr.done td { background: rgba(201, 162, 74, .05) }
.ltab tbody tr.done .nm, .ltab tbody tr.done label { color: var(--txt-muted) }
.ltab input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--gold) }
/* 勾选框本体只有 20px，但**点击区是包着它的 label**，按触屏底线给到 44×44 */
.lchk { display: flex; align-items: center; justify-content: center;
  min-width: 44px; min-height: 44px; cursor: pointer }
.board .c-chk { width: 44px }
/* 挑战矩阵：一格一条，勾在中间。表格那套 .board 的窄屏 min-width 不带进来，
   四列本来就窄，横滚反而会把"这一组一眼看完"这件事毁掉。 */
.lmtxwrap { overflow-x: auto }
/* 全站那条 `th{position:sticky;top:var(--hd-h)}`（app.css:253）在横滚容器里会把
   头几行的表头格**往下推**到 top 值（容器不产生纵向滚动，sticky 的参照物变成它自己，
   2026-10-26 实拍：列头新手/熟练/高阶跑到第三行、头两行的归属名叠成一格）。
   照 app.css:267 那套：横滚容器里纵向吸顶写 static，首列改左吸顶；
   首列左吸顶那条必须同时写 top:auto——只写 left 的话全局那条 top 还在，照样往下推。 */
.lmtx thead th { position: static }
.lmtx th.lmtxsub { position: sticky; left: 0; top: auto; z-index: 2 }
.lmtx thead th.lmtxsub { z-index: 3 }
.lmtx { border-collapse: collapse; width: 100%; max-width: 620px }
.lmtx th, .lmtx td { border: 1px solid var(--line); text-align: center; padding: 0 }
.lmtx thead th { background: var(--sunk); color: var(--lead);
  font: 600 12.5px var(--font-mono); padding: 7px 10px; white-space: nowrap }
.lmtxsub { text-align: left !important; padding: 0 12px !important; white-space: nowrap;
  font-weight: 600; color: var(--txt-title); background: var(--sunk) }
.lmtxcell { width: 100%; height: 44px }
/* 格子里只留原生勾选框一个视觉：上一版在框旁边又画了个 14px 的装饰方块，
   实拍里一格两个框，看不出哪个才是能点的（2026-10-26）。勾选态靠 accent-color + 整格底色。 */
.lmtxcell input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--gold) }
.lmtx td.done { background: color-mix(in srgb, var(--gold) 12%, transparent) }
.lmtxread { margin: 10px 0 0; min-height: 20px }
/* 常见问答：dt 问、dd 答，不引第三方那句现成 FAQ（红线：别人的说明文本不搬） */
.lge-qa { margin: 6px 0 0 }
.lge-qa dt { font-weight: 700; color: var(--txt-title); margin-top: 14px }
.lge-qa dt:first-child { margin-top: 4px }
.lge-qa dd { margin: 4px 0 0; color: var(--txt); line-height: 1.75 }
.lge-special { border-color: var(--line-2) }
/* 这一张只有一行、五列，不需要 .board 在窄屏那条 min-width:640px——
   留着它会把 375 的布局视口顶到 674（Chrome 于是整体缩放，"整页不横溢"那条断言反而还是 0） */
.lge-sptab { min-width: 0 }
/* 轻提示 */
.lge-toast { position: fixed; left: 50%; transform: translateX(-50%); bottom: 26px; z-index: 40;
  background: var(--panel); border: 1px solid var(--gold-deep); color: var(--txt-title);
  padding: 9px 14px; border-radius: 6px; font-size: 13px; max-width: min(92vw, 560px) }
.lge-toast-enter-active, .lge-toast-leave-active { transition: opacity .18s, transform .18s }
.lge-toast-enter-from, .lge-toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(6px) }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0) }
@media (max-width: 899px) {
  .lge-plans { flex-direction: column; align-items: stretch }
  .lge-planact { flex-wrap: wrap }
  .lgr-i { flex: 1 1 46% }
}
</style>
