const fs = require('fs');
const path = require('path');
const engine = require('../../for-mini/services/talent-engine');

function levelingBuilds(dataDir) {
  const read = (name) => JSON.parse(fs.readFileSync(path.join(dataDir, name), 'utf8'));
  const { meta, featured, features, mainTalents, builds } = read('leveling-talents.json');
  const classes = read('classes.json').classes;
  const classMap = new Map(classes.map((c) => [c.id, c]));
  const found = new Map();
  if (!meta.source.author || !/^https:\/\//.test(meta.source.url) || !/^\d{4}-\d{2}-\d{2}$/.test(meta.source.checkedAt)) {
    throw new Error('练级天赋缺来源或核对日期');
  }
  for (const build of builds) {
    const { classId, picks } = build;
    const klass = classMap.get(classId);
    if (!klass || found.has(classId) || !build.name || !/^[a-f0-9]{64}$/.test(build.sha256)) {
      throw new Error('练级天赋职业或来源有误：' + classId);
    }
    const data = read('talents/' + classId + '.json');
    const states = new Map(picks);
    const total = picks.reduce((sum, row) => sum + row[1], 0);
    if (states.size !== picks.length || total > data.rules.totalPoints || (build.complete && total !== data.rules.totalPoints)) {
      throw new Error('练级天赋点数有误：' + classId);
    }
    const trees = [];
    let matched = 0;
    data.trees.forEach((tree) => {
      const selected = tree.nodes.filter((node) => states.has(node.id)).sort((a, b) => a.tier - b.tier || a.column - b.column);
      if (!selected.length) return;
      for (const node of selected) {
        const rank = states.get(node.id);
        if (!Number.isInteger(rank) || rank < 1 || rank > node.maxRanks || !node.nameCn) {
          throw new Error('练级天赋节点点数有误：' + node.id);
        }
        if (build.complete) {
          const below = selected.filter((n) => n.tier < node.tier).reduce((sum, n) => sum + states.get(n.id), 0);
          if (below < data.rules.tierUnlockCost[node.tier] || (node.requires || []).some((id) => !states.has(id))) {
            throw new Error('练级天赋与当前树的层级或前置有出入：' + node.id);
          }
        }
      }
      matched += selected.length;
      trees.push({
        id: tree.id, name: tree.nameCn,
        total: selected.reduce((sum, node) => sum + states.get(node.id), 0),
        picks: selected.map((node) => ({ id: node.id, name: node.nameCn, rank: states.get(node.id), max: node.maxRanks }))
      });
    });
    if (!matched || matched !== picks.length) throw new Error('练级天赋有无法匹配的节点：' + classId);
    const mainTree = trees.reduce((main, tree) => tree.total > main.total ? tree : main);
    const mainTalent = data.trees.find((tree) => tree.id === mainTree.id).nodes.find((node) => node.id === mainTalents[classId]);
    const feature = features[classId];
    if (!mainTalent || !states.has(mainTalent.id) || !mainTalent.iconKey || !klass.iconKey
      || typeof feature !== 'string' || !feature.trim()) {
      throw new Error('练级天赋缺特点、职业图标或主系已选天赋图标：' + classId);
    }
    found.set(classId, {
      classId, className: klass.cn, name: build.name, total, complete: !!build.complete, trees,
      feature, classIconKey: klass.iconKey, mainIconKey: mainTalent.iconKey,
      mainTreeName: mainTree.name, mainTalentName: mainTalent.nameCn,
      code: engine.encode(data.trees, Object.fromEntries(states)), layout: engine.layoutKey(data.trees)
    });
  }
  if (found.size !== classMap.size || !featured.length || featured.length > 3
    || new Set(featured).size !== featured.length
    || featured.some((id) => !found.has(id))) {
    throw new Error('练级天赋职业覆盖或首页推荐名单有误');
  }
  return {
    source: { author: meta.source.author, publishedAt: meta.source.publishedAt, url: meta.source.url },
    builds: Array.from(found.values()),
    featured: featured.map((id) => {
      const { classId, className, name, feature } = found.get(id);
      return { classId, className, name, feature };
    })
  };
}

module.exports = levelingBuilds;
