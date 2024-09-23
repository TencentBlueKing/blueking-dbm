<template>
  <div>
    <div
      v-for="item in data"
      :key="item.ip"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <HightLightText
          :key-word="keyWord"
          :text="item.ip" />
        <div class="intro">({{ t('主机') }})</div>
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { systemSearchCache } from '@common/cache';

  import { useRedirect } from '@components/system-search/hooks/useRedirect';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    keyWord: string;
    data: {
      bk_biz_id: number;
      ip: string;
      cluster_type: string;
      cluster_id: number;
    }[];
    bizIdNameMap: Record<number, string>;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const handleRedirect = useRedirect();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.ip);

    handleRedirect(
      data.cluster_type,
      {
        instance: data.ip,
      },
      data.bk_biz_id,
    );
  };
</script>
