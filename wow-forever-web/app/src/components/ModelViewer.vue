<script setup>
/* 配装 3D 查看器（2026-10-26 站主"先给我看 3D 效果"那一问的脚手架）。
   三条硬要求：
   ① three.js 与模型**都懒加载**——不点这个按钮，页面一个 3D 字节都不下载；
   ② 没有 WebGL / 加载失败 → 退回静态图并说一句原因，不白屏、不假装有模型；
   ③ 染色与显隐全部由父级传进来的 gear（节点名 → 品质）决定，本站不在这抄颜色值。
   占位模型按 gear 控制显隐与染色；客户端整人模型保留原材质、显示完整网格。 */
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { qualityColor } from '../lib/bis-model.js';

const props = defineProps({
  src: { type: String, required: true },
  kind: { type: String, default: 'placeholder' },
  gear: { type: Object, default: () => ({}) },
  height: { type: Number, default: 340 }
});
const emit = defineEmits(['ready', 'fail']);

const box = ref(null);
const busy = ref(true);
const why = ref('');
let renderer = null, scene = null, camera = null, root = null, raf = 0;
let ro = null, dragging = false, lastX = 0, yaw = 0.6, pitch = 0.06, spin = 0.004;
const disposables = [];

function paint(node) {
  // 只处理网格：gltf.scene 的根是个带名字的组节点（"bis-placeholder"），
  // 上一版没判 isMesh，把它也当成"没穿的部位"藏了 → 整个模型一个像素都不出，
  // 而 canvas、分包、按钮状态全都正常，光看 DOM 查不出来（2026-10-26 实拍抓到）。
  if (!node.isMesh) return;
  if (node.name.indexOf('body_') === 0) return;   // 身体不参与染色，永远可见
  const g = props.gear[node.name];
  if (!g) { node.visible = false; return; }       // 这一套没穿这个部位 → 不画
  node.visible = true;
  const c = qualityColor(g.quality);
  node.traverse((m) => {
    if (!m.isMesh) return;
    if (!m.material || !m.material.isMeshStandardMaterial) return;
    m.material = m.material.clone();
    m.material.color.set(c);
    m.material.emissive = m.material.emissive || null;
    if (m.material.emissive) m.material.emissive.set(c);
    m.material.emissiveIntensity = 0.22;
    disposables.push(m.material);
  });
}

function apply() {
  if (!root) return;
  root.rotation.set(pitch, yaw, 0);
}

function loop() {
  if (!dragging && root) { yaw += spin; apply(); }
  if (renderer) renderer.render(scene, camera);
  raf = requestAnimationFrame(loop);
}

function fit() {
  if (!renderer || !box.value) return;
  const w = box.value.clientWidth || 300;
  const h = props.height;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function onDown(e) { dragging = true; lastX = e.clientX; e.preventDefault(); }
function onMove(e) {
  if (!dragging) return;
  yaw += (e.clientX - lastX) * 0.01;
  lastX = e.clientX;
  apply();
}
function onUp() { dragging = false; }

function fail(msg) {
  busy.value = false;
  why.value = msg;
  const canvas = box.value && box.value.querySelector('canvas.pzc-gl');
  if (canvas) canvas.remove();
  emit('fail', msg);
}

onMounted(async () => {
  let THREE, GLTFLoader;
  try {
    THREE = await import('three');
    ({ GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js'));
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) throw new Error('这台设备的浏览器没有可用的 WebGL');
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    canvas.className = 'pzc-gl';
    box.value.appendChild(canvas);
    scene = new THREE.Scene();
    if (props.kind === 'real') scene.background = new THREE.Color(0x111b29);
    camera = new THREE.PerspectiveCamera(34, 1, 0.1, 30);
    camera.position.set(0, 1.02, 3.05);
    scene.add(new THREE.AmbientLight(0xffffff, 1.15));
    const key = new THREE.DirectionalLight(0xffffff, 1.5);
    key.position.set(1.6, 2.4, 2.2);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x9fb6d8, 0.7);
    fill.position.set(-1.8, 1.0, -1.4);
    scene.add(fill);
    canvas.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    ro = new ResizeObserver(fit);
    ro.observe(box.value);
    fit();
    new GLTFLoader().load(props.src, (gltf) => {
      root = new THREE.Group();
      root.add(gltf.scene);
      if (props.kind === 'real') {
        const bounds = new THREE.Box3().setFromObject(gltf.scene);
        const size = bounds.getSize(new THREE.Vector3());
        const center = bounds.getCenter(new THREE.Vector3());
        gltf.scene.position.sub(center);
        const halfFov = camera.fov * Math.PI / 360;
        const distance = Math.max(size.y / 2, size.x / (2 * camera.aspect)) * 1.25 / Math.tan(halfFov);
        camera.position.set(0, 0, distance);
        camera.lookAt(0, 0, 0);
        // 客户端导出的整人模型正面朝 +X；本站相机朝 -Z 看。
        yaw = -Math.PI / 2;
        pitch = 0;
        spin = 0;
      } else {
        gltf.scene.traverse((n) => { if (n.name) paint(n); });
      }
      scene.add(root);
      apply();
      busy.value = false;
      emit('ready', { nodes: gltf.scene.children.length });
      loop();
    }, undefined, (err) => {
      // 这条是异步回调，throw 到不了外面的 try/catch，必须自己收口
      fail('模型没加载出来（' + ((err && err.message) || props.src) + '）');
    });
  } catch (e) {
    fail((e && e.message) || String(e));
  }
});

onBeforeUnmount(() => {
  cancelAnimationFrame(raf);
  if (ro) ro.disconnect();
  disposables.forEach((m) => m.dispose && m.dispose());
  if (renderer) { renderer.dispose(); renderer.forceContextLoss && renderer.forceContextLoss(); }
  const c = box.value && box.value.querySelector('canvas');
  if (c) {
    c.removeEventListener('pointerdown', onDown);
    c.remove();
  }
  window.removeEventListener('pointermove', onMove);
  window.removeEventListener('pointerup', onUp);
  renderer = null;
});

</script>

<template>
  <div ref="box" class="pzc-glbox" :style="{ height: height + 'px' }" role="img"
       :aria-label="why ? '三维模型没显示出来：' + why : '三维配装模型，可拖动旋转'">
    <p v-if="busy" class="pzc-glhint dim">正在装载模型…</p>
    <!-- 失败时这里什么都不画（父级拿到 fail 后会在图下面写明原因），
         画布本身也不留在页面上，免得挡着背后那张原画 -->
  </div>
</template>

<style scoped>
.pzc-glbox { position: relative; width: 100%; }
.pzc-glbox :deep(.pzc-gl) { display: block; width: 100%; height: 100%; cursor: grab; touch-action: pan-y }
.pzc-glbox :deep(.pzc-gl:active) { cursor: grabbing }
.pzc-glhint { position: absolute; left: 10px; right: 10px; bottom: 8px; margin: 0;
  font-size: 12px; color: var(--txt-dim); text-align: center }
</style>
