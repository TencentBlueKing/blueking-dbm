<template>
  <!-- srcdoc 默认继承父页面同源权限，sandbox 只放开 allow-scripts（不可加 allow-same-origin）以隔离 content 中的脚本 -->
  <iframe
    class="report-share-html-frame"
    sandbox="allow-scripts"
    :srcdoc="srcdoc" />
</template>
<script setup lang="ts">
  interface Props {
    content: string;
  }

  const props = defineProps<Props>();

  // srcdoc 页面的基地址为 about:srcdoc，锚点链接的默认跳转行为无效，改由 JS 滚动定位
  const anchorScript = `
<script>
  document.addEventListener('click', (event) => {
    const link = event.target.closest && event.target.closest('a[href^="#"]');
    if (!link) {
      return;
    }
    event.preventDefault();
    const id = decodeURIComponent(link.getAttribute('href').slice(1));
    const target = id ? document.getElementById(id) : document.body;
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
<\u002Fscript>`;

  const srcdoc = computed(() => (props.content ? props.content + anchorScript : ''));
</script>
<style lang="postcss">
  .report-share-html-frame {
    display: block;
    width: 100%;
    height: calc(100vh - 102px - var(--notice-height));
    border: none;
  }
</style>
