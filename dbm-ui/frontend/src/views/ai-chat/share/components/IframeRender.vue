<template>
  <iframe
    class="report-share-html-frame"
    :srcdoc="content" />
</template>
<script setup lang="ts">
  interface Props {
    content: string;
  }

  defineProps<Props>();
</script>
<style lang="postcss">
  .report-share-html-frame {
    display: block;
    width: 100%;
    height: calc(100vh - 102px - var(--notice-height));
    border: none;
  }
</style>
