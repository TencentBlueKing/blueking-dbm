<template>
  <div
    v-if="clusters.length > 0"
    class="related-clusters-main">
    <div class="item-info">— {{ t('同机关联集群') }}：</div>
    <RenderRow
      v-for="(item, index) in clusters"
      :key="index">
      <div class="item-info">— {{ item }}</div>
    </RenderRow>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderRow from '@components/text-overflow-layout/Index.vue';

  interface Props {
    clusters: string[];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .related-clusters-main {
    font-size: 12px;
    color: #979ba5;

    .item-info {
      height: 20px;
      line-height: 20px;
    }
  }
</style>
