/* 倒计时：顶栏 chip 与首页那块共用同一个读数，每秒刷一次，卸载时清掉定时器。
   旧站是 setInterval 直接改节点文本，这里换成响应式值，组件里不用再手写定时器。 */
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { launchLeft } from './fmt.js';

export function useCountdown() {
  const left = ref(launchLeft());
  let timer = null;
  const start = () => {
    if (timer) return;
    timer = setInterval(() => { left.value = launchLeft(); }, 1000);
  };
  const stop = () => {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  };
  onMounted(start);
  onBeforeUnmount(stop);
  return { left, start, stop };
}
