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
    <Total
      :count="count"
      @to-result="handleToResult" />
  </div>
</template>
<script setup lang="ts">
  import { systemSearchCache } from '@common/cache';

  import TextHighlight from '@components/text-highlight/Index.vue';

  import { getBusinessHref } from '@utils';

  import Total from './components/Total.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    count: number;
    data: {
      bk_biz_id: number;
      id: number;
      ticket_type: string;
    }[];
    keyWord: string;
  }

  type Emits = (e: 'to-result', resourceType: string) => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const router = useRouter();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(`${data.id}`);

    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.id,
      },
    });
    // 业务 id 为空时保持原地址，不替换成当前业务
    window.open(data.bk_biz_id ? getBusinessHref(href, data.bk_biz_id) : href);
  };

  const handleToResult = () => {
    emits('to-result', 'ticket');
  };
</script>
