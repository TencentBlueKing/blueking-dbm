<template>
  <div>
    <div
      v-for="item in data"
      :key="item.id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <span>#</span>
        <TextHighlight
          :keyword="keyWord"
          :text="`${item.id}`" />
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

  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: {
      bk_biz_id: number;
      id: number;
      ticket_type: string;
    }[];
    keyWord: string;
  }

  defineProps<Props>();

  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(`${data.id}`);

    location(
      {
        name: 'bizTicketManage',
        params: {
          ticketId: data.id,
        },
      },
      data.bk_biz_id,
    );
  };
</script>
