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
        <div class="intro">
          (主机)
        </div>
      </div>
      <div class="biz-text">
        {{ bizIdNameMap[item.bk_biz_id] }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { systemSearchCache } from '@common/cache';

  import HightLightText from './components/HightLightText.vue';
  import useLocation from './hooks/useLocation';

  interface Props {
    keyWord: string,
    data: {
      bk_biz_id: number,
      ip: string,
      cluster_type: string,
      machine_type: string,
    }[],
    bizIdNameMap: Record<number, string>
  }

  defineProps<Props>();

  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.ip);
    console.log('location = ', location);
  };
</script>

