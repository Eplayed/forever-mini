/* 本地假 OSS：把 tools/oss-release.js 构建出来的批次按真 HTTP 语义发出去
   （ETag = 实际字节的 MD5、Content-Length、Cache-Control、404），
   用来在微信开发者工具里验 live 路径与 ETag 校验。只监听 127.0.0.1，不写任何东西。
   模式：FAKE_OSS_MODE=normal|tamper|min99|dropdetail */
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = '/Users/zhangyajun/Documents/project/wow-forever/for-mini/oss-build/beta';
const MODE = process.env.FAKE_OSS_MODE || 'normal';
const BIDX = JSON.parse(fs.readFileSync(require('path').join(ROOT, 'manifest.json'), 'utf8')).buildId;
const PORT = Number(process.env.FAKE_OSS_PORT || 8899);
const md5u = (b) => crypto.createHash('md5').update(b).digest('hex').toUpperCase();

const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(req.url.replace(/^\/+/, '').replace(/^wow\/beta\/v1\//, ''));
  const file = path.join(ROOT, rel);
  if (!file.startsWith(ROOT) || !fs.existsSync(file)) {
    res.writeHead(404, { 'Content-Type': 'application/xml' });
    res.end('<Error><Code>NoSuchKey</Code></Error>');
    return;
  }
  let buf = fs.readFileSync(file);
  if (MODE === 'tamperindex' && rel === 'builds/' + BIDX + '/dungeons/index.json') {
    const j = JSON.parse(buf.toString('utf8'));
    j.items[0].nameCn = '被改过的副本名';
    buf = Buffer.from(JSON.stringify(j, null, 1) + '\n', 'utf8');
  }
  if ((MODE === 'tamper' || MODE === 'tamperboth') && /dungeons\/(detail|loot)\/ragefire-chasm\.json$/.test(rel)) {
    const j = JSON.parse(buf.toString('utf8'));
    if (j.dungeon && j.dungeon.bosses && j.dungeon.bosses.length) j.dungeon.bosses[0].nameCn = '被改过的首领名';
    if (j.drops && j.drops.length) j.drops[0].nameCn = '被改过的掉落名';
    buf = Buffer.from(JSON.stringify(j, null, 1) + '\n', 'utf8');
  }
  if ((MODE === 'tamperindex' || MODE === 'tamperboth') && rel === 'manifest.json') {
    /* 索引被改时指针里的入口校验值也必须跟着变，否则测不到"整批不显示" */
    const j = JSON.parse(buf.toString('utf8'));
    j.fetch.dungeonIndex.etag = '00000000000000000000000000000000';
    buf = Buffer.from(JSON.stringify(j, null, 1) + '\n', 'utf8');
  }
  if (MODE === 'min99' && rel === 'manifest.json') {
    const j = JSON.parse(buf.toString('utf8'));
    j.minClientSchemaVersion = 99;
    buf = Buffer.from(JSON.stringify(j, null, 1) + '\n', 'utf8');
  }
  if (MODE === 'dropdetail' && /dungeons\/detail\/ragefire-chasm\.json$/.test(rel)) {
    res.writeHead(404, { 'Content-Type': 'application/xml' });
    res.end('<Error><Code>NoSuchKey</Code></Error>');
    return;
  }
  /* FAKE_OSS_NOCACHE=1：不给 Cache-Control，让换模式（篡改/新版本）立刻可见。
     默认照真 OSS 一样发 immutable —— 批次文件本就该被缓存一年。 */
  const noCache = process.env.FAKE_OSS_NOCACHE === '1';
  const immutable = rel.indexOf('builds/') === 0;
  res.writeHead(200, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': buf.length,
    ETag: '"' + md5u(buf) + '"',
    'Cache-Control': noCache ? 'no-store' : (immutable ? 'public, max-age=31536000, immutable' : 'public, max-age=60, must-revalidate'),
    'Last-Modified': new Date().toUTCString(),
    'x-fake-oss': MODE
  });
  res.end(buf);
});

server.listen(PORT, '127.0.0.1', () => {
  process.stdout.write('假 OSS 监听 http://127.0.0.1:' + PORT + ' 模式 ' + MODE + ' 根 ' + ROOT + '\n');
});
