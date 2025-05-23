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
      </div>
      <div class="biz-text">
        {{ item.poolDispaly }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useLocation } from '@hooks';

  import { systemSearchCache } from '@common/cache';

  import HightLightText from './components/HightLightText.vue';

  interface Props {
    data: {
      ip: string;
      poolDispaly: string;
    }[];
    keyWord: string;
  }

  defineProps<Props>();

  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.ip);

    location({
      name: 'allHost',
      query: {
        ips: data.ip,
      },
    });
  };
</script>
