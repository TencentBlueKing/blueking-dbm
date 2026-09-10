<template>
  <!-- srcdoc 默认继承父页面同源权限，sandbox 不放开 allow-same-origin 以隔离 content 中的脚本 -->
  <!-- allow-popups 允许内容里的链接新开窗口，escape-sandbox 让新窗口不再继承沙箱（否则目标页 origin 为 null） -->
  <iframe
    class="report-share-html-frame"
    sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
    :srcdoc="srcdoc" />
</template>
<script setup lang="ts">
  interface Props {
    content: string;
  }

  const props = defineProps<Props>();

  // srcdoc 页面的基地址继承父页面 URL，链接的默认跳转行为都不符合预期，统一接管点击
  const linkScript = `
<script>
  document.addEventListener('click', (event) => {
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
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      return;
    }
    // 在沙箱内跳转会以 null origin 加载目标页，只能新开标签页；其余协议（javascript: 等）保持默认行为
    if (link.protocol === 'http:' || link.protocol === 'https:') {
      event.preventDefault();
      window.open(link.href, '_blank', 'noopener');
    }
  });
<\u002Fscript>`;

  const srcdoc = computed(() => (props.content ? props.content + linkScript : ''));
</script>
<style lang="postcss">
  .report-share-html-frame {
    display: block;
    width: 100%;
    height: calc(100vh - 102px - var(--notice-height));
    border: none;
  }
</style>
