/* 数据层：运行时读 src/data/*.json 同步到 app/public/data 的副本。
   与旧站 data.js 行为一致——同一份 JSON 只请求一次（含并发去重），失败时抛错让页面显示失败态。
   数据真相仍然只有 ../src/data 那一处，本文件不做任何加工。 */
const cache = new Map();

export function assetUrl(rel) {
  const base = import.meta.env.BASE_URL || './';
  return base + String(rel).replace(/^\//, '');
}

export function load(file) {
  const url = assetUrl(file);
  if (cache.has(url)) return cache.get(url);
  const p = fetch(url).then((res) => {
    if (!res.ok) {
      cache.delete(url);
      throw new Error(res.status + ' ' + url);
    }
    return res.json();
  }).catch((e) => {
    cache.delete(url);
    throw e;
  });
  cache.set(url, p);
  return p;
}

export function loadAll(files) {
  return Promise.all(files.map((f) => load(f)));
}

/* 单测与对拍脚本要看"到底请求了哪几份数据"，别靠猜 */
export function loadedKeys() {
  return [...cache.keys()].map((k) => k.split('/').pop());
}

export function forget(file) {
  cache.delete(assetUrl(file));
}
