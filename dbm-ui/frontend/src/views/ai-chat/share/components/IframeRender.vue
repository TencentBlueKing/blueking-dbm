<template>
  <!-- srcdoc 默认继承父页面同源权限，sandbox 不放开 allow-same-origin 以隔离 content 中的脚本 -->
  <!-- allow-popups 允许内容里的链接新开窗口，escape-sandbox 让新窗口不再继承沙箱（否则目标页 origin 为 null） -->
  <iframe
    ref="iframe"
    class="report-share-html-frame"
    sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
    :srcdoc="srcdoc"
    :style="autoHeight ? { height: `${frameHeight}px` } : undefined" />
</template>
<script setup lang="ts">
  interface Props {
    // 高度随内容撑开，由使用方的滚动容器滚动，iframe 自身不出滚动条
    autoHeight?: boolean;
    content: string;
  }

  // anchor：autoHeight 下锚点定位的目标位置（相对 iframe 顶部），由使用方滚动自己的容器
  // panel-change：autoHeight 下内容中带 data-dbm-panel 属性的元素被点击
  type Emits = {
    (e: 'anchor', top: number): void;
    (e: 'panel-change', panel: string): void;
  };

  const props = withDefaults(defineProps<Props>(), {
    autoHeight: false,
  });
  const emits = defineEmits<Emits>();

  const iframeRef = useTemplateRef('iframe');
  const frameHeight = ref(0);

  // srcdoc 页面的基地址继承父页面 URL，链接的默认跳转行为都不符合预期，统一接管点击
  const createLinkScript = (autoHeight: boolean) => `
<script>
(() => {
  const AUTO_HEIGHT = ${autoHeight};
  const post = (data) => window.parent.postMessage(data, '*');
  if (AUTO_HEIGHT) {
    document.documentElement.style.overflow = 'hidden';
    new ResizeObserver(() => {
      post({ type: 'height', height: document.documentElement.scrollHeight });
    }).observe(document.documentElement);
  }
  document.addEventListener('click', (event) => {
    // 只在嵌入宿主页面（autoHeight）时接管，独立展示时保持元素原有行为
    const panelElement = AUTO_HEIGHT && event.target.closest && event.target.closest('[data-dbm-panel]');
    if (panelElement) {
      event.preventDefault();
      post({ type: 'panel', panel: panelElement.getAttribute('data-dbm-panel') });
      return;
    }
    const link = event.target.closest && event.target.closest('a[href]');
    if (!link) {
      return;
    }
    const href = link.getAttribute('href');
    // 锚点链接会跳到父页面地址而非当前文档，改由 JS 滚动定位
    if (href.startsWith('#')) {
      event.preventDefault();
      const id = decodeURIComponent(href.slice(1));
      const target = id ? document.getElementById(id) : document.body;
      if (target) {
        // iframe 不滚动时 scrollIntoView 带不动宿主页面，交给父页面滚动
        if (AUTO_HEIGHT) {
          post({ type: 'anchor', top: target.getBoundingClientRect().top + window.scrollY });
        } else {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
      return;
    }
    // 在沙箱内跳转会以 null origin 加载目标页，只能新开标签页；其余协议（javascript: 等）保持默认行为
    if (link.protocol === 'http:' || link.protocol === 'https:') {
      event.preventDefault();
      window.open(link.href, '_blank', 'noopener');
    }
  });
})();
<\u002Fscript>`;

  const srcdoc = computed(() => (props.content ? props.content + createLinkScript(props.autoHeight) : ''));

  // 沙箱 iframe 的 origin 为 null，只能按消息来源窗口校验
  const handleMessage = (event: MessageEvent) => {
    if (!iframeRef.value || event.source !== iframeRef.value.contentWindow) {
      return;
    }
    const data = event.data as { height?: unknown; panel?: unknown; top?: unknown; type?: unknown };
    if (data?.type === 'height' && props.autoHeight && typeof data.height === 'number') {
      frameHeight.value = data.height;
      return;
    }
    if (data?.type === 'anchor' && typeof data.top === 'number') {
      emits('anchor', data.top);
      return;
    }
    if (data?.type === 'panel' && typeof data.panel === 'string' && data.panel) {
      emits('panel-change', data.panel);
    }
  };

  onMounted(() => {
    window.addEventListener('message', handleMessage);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('message', handleMessage);
  });
</script>
<style lang="postcss">
  .report-share-html-frame {
    display: block;
    width: 100%;
    height: calc(100vh - 102px - var(--notice-height));
    border: none;
  }
</style>
