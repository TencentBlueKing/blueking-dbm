<template>
  <div>
    <div
      v-for="item in data"
      :key="item.id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <span>#</span>
        <HightLightText
          :key-word="keyWord"
          :text="`${item.id}`" />
        <div class="intro">({{ t('单据') }})</div>
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useLocation } from '@hooks';

  import { systemSearchCache } from '@common/cache';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    keyWord: string;
    data: {
      bk_biz_id: number;
      id: number;
      ticket_type: string;
    }[];
    bizIdNameMap: Record<number, string>;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(`${data.id}`);

    location(
      {
        name: 'bizTicketManage',
        query: {
          id: data.id,
        },
      },
      data.bk_biz_id,
    );
  };
</script>
