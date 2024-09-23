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
        <div class="intro">({{ t('资源池主机') }})</div>
      </div>
      <div class="biz-text">
        {{ t('资源池') }}
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
      ip: string;
    }[];
  }

  defineProps<Props>();

  const { t } = useI18n();
  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.ip);

    location({
      name: 'resourcePool',
      query: {
        hosts: data.ip,
      },
    });
  };
</script>
