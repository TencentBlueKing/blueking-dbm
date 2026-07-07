<template>
  <div>
    <div
      v-for="item in data"
      :key="item.id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <TextHighlight
          :keyword="keyWord"
          :text="item.displayValue" />
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';

  import { systemSearchCache } from '@common/cache';

  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: QuickSearchClusterModel[];
    keyWord: string;
  }

  defineProps<Props>();

  const handleRedirect = useRedirect();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.name);

    handleRedirect(
      data.cluster_type,
      {
        domain: data.displayValue,
      },
      data.bk_biz_id,
    );
  };
</script>
