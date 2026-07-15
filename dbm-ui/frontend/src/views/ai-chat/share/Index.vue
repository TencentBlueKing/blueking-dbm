<template>
  <IframeRender
    v-if="isHtml"
    :content="content" />
  <MarkdownRender
    v-else
    :content="content" />
  <Teleport to=".db-navigation-content-title">
    {{ reportShare?.title || 'DBA 智能助手内容分享' }}
  </Teleport>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getReportShare } from '@services/source/dbReport';

  import IframeRender from './components/IframeRender.vue';
  import MarkdownRender from './components/MarkdownRender.vue';

  const route = useRoute();
  const recordId = route.params.recordId as string;

  const { data: reportShare } = useRequest(getReportShare, {
    defaultParams: [
      {
        record_id: recordId,
      },
    ],
  });

  // 完整的 html 页面通过 iframe 隔离渲染，避免与宿主页面样式冲突且保留 html/head/body 结构
  const isHtml = computed(() => reportShare.value?.format === 'html');

  const content = computed(() => reportShare.value?.content ?? '');
</script>
