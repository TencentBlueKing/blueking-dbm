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
          :text="item.master_domain" />
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
    <Total
      :count="count"
      @to-result="handleToResult" />
  </div>
</template>
<script setup lang="ts">
  import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';

  import { systemSearchCache } from '@common/cache';

  import { useRedirect } from '@components/system-search/hooks/useRedirect';
  import TextHighlight from '@components/text-highlight/Index.vue';

  import Total from './components/Total.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    count: number;
    data: QuickSearchClusterModel[];
    keyWord: string;
  }

  type Emits = (e: 'to-result', resourceType: string) => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const handleRedirect = useRedirect();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.name);

    handleRedirect(
      data.cluster_type,
      {
        domain: data.master_domain,
      },
      data.bk_biz_id,
    );
  };

  const handleToResult = () => {
    emits('to-result', 'cluster');
  };
</script>
