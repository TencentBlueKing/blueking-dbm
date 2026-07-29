<template>
  <div>
    <div
      v-for="item in data"
      :key="item.root_id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <span>#</span>
        <TextHighlight
          :keyword="keyWord"
          :text="item.root_id" />
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
  import { useLocation } from '@hooks';

  import { systemSearchCache } from '@common/cache';

  import TextHighlight from '@components/text-highlight/Index.vue';

  import Total from './components/Total.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    count: number;
    data: {
      bk_biz_id: number;
      root_id: string;
      ticket_type: string;
    }[];
    keyWord: string;
  }

  type Emits = (e: 'to-result', resourceType: string) => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.root_id);

    location(
      {
        name: 'taskHistoryDetail',
        params: {
          root_id: data.root_id,
        },
      },
      data.bk_biz_id,
    );
  };

  const handleToResult = () => {
    emits('to-result', 'task');
  };
</script>
