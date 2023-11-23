<template>
  <div>
    <div
      v-for="item in data"
      :key="item.id"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <HightLightText
          :key-word="keyWord"
          :text="getMatchText(item)" />
        <div class="intro">
          (实例<span v-if="item.cluster_domain">, {{ item.cluster_domain }}</span>)
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
      cluster_id: number,
      cluster_type: string,
      id: number,
      ip: string,
      name: string,
      port: string,
      cluster_domain: string,
    }[],
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const location = useLocation();

  const getMatchText = (data: Props['data'][number]) => {
    if (data.name.indexOf(props.keyWord) > -1) {
      return data.name;
    }
    return `${data.ip}:${data.port}`;
  };

  const handleGo = (data: Props['data'][number]) => {
    systemSearchCache.appendItem(data.name);
    if (data.cluster_type === 'es') {
      location({
        name: 'EsList',
        params: {
          clusterId: data.cluster_id,
          instanceAddress: `${data.ip}:${data.port}`,
        },
      });
    } else if (data.cluster_type === 'influxdb') {
      location({
        name: 'InfluxDBInstDetails',
        params: {
          instId: data.id,
        },
      });
    }
  };
</script>

