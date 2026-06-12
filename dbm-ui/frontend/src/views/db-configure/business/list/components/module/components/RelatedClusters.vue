<template>
  <span class="module-info-item related-clusters-wrapper">
    <span class="module-info-label">{{ t('关联集群') }}：</span>
    <span
      v-if="relatedClusterCount > 0"
      ref="relatedClustersRef"
      class="related-clusters-count">
      {{ relatedClusterCount }}
    </span>
    <span v-else>--</span>
  </span>
</template>

<script setup lang="ts">
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { dbTippy } from '@common/tippy';

  interface Props {
    relatedClusterCount: number;
    relatedClusters: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  /** 关联集群 tooltip 纵向展示 */
  const relatedClustersRef = ref<HTMLElement>();
  let relatedClustersTippy: Instance | null = null;

  const relatedClustersTooltip = computed(() => {
    if (!props.relatedClusters) return '';
    const items = props.relatedClusters.split(', ');
    return `
      <div class="related-clusters-tooltip">
        <div class="related-clusters-list">
          ${items.map((name: string) => `<div class="related-cluster-item">${name}</div>`).join('')}
        </div>
      </div>
    `;
  });

  watchPostEffect(() => {
    const el = relatedClustersRef.value;
    const content = relatedClustersTooltip.value;
    relatedClustersTippy?.destroy();
    relatedClustersTippy = null;
    if (el && content) {
      relatedClustersTippy = dbTippy(el, {
        allowHTML: true,
        appendTo: () => document.body,
        arrow: true,
        content,
        hideOnClick: true,
        interactive: true,
        placement: 'top',
        trigger: 'mouseenter click',
        zIndex: 9999,
      });
    }
  });

  onUnmounted(() => {
    relatedClustersTippy?.destroy();
  });
</script>

<style lang="less" scoped>
  .related-clusters-wrapper {
    .related-clusters-count {
      margin-left: 4px;
      font-weight: 700;
      color: #3a84ff;
      cursor: default;
    }
  }
</style>
