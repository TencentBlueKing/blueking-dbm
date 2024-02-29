<template>
  <div>
    <div
      v-for="item in data"
      :key="item.root_id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <span>#</span>
        <HightLightText
          :key-word="keyWord"
          :text="item.root_id" />
        <div class="intro">(任务ID)</div>
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useLocation } from '@hooks';

  import { systemSearchCache } from '@common/cache';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    keyWord: string;
    data: {
      bk_biz_id: number;
      root_id: string;
      ticket_type: string;
    }[];
    bizIdNameMap: Record<number, string>;
  }

  defineProps<Props>();

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
</script>
