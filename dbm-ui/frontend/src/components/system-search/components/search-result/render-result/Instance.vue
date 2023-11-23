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
    const routerNameMap = {
      TwemproxyRedisInstance: 'DatabaseRedisList',
      tendbha: 'DatabaseTendbha',
      tendbsingle: 'DatabaseTendbsingle',
      tendbcluster: 'tendbClusterList',
      es: 'EsList',
      kafka: 'KafkaList',
      hdfs: 'HdfsList',
      pulsar: 'PulsarList',
      redis: 'DatabaseRedisList',
      influxdb: 'InfluxDBInstDetails',
    } as Record<string, string>;

    if (data.cluster_type === 'tendbha') {
      location({
        name: 'DatabaseTendbhaInstance',
        query: {
          ip: data.ip,
        },
      }, data.bk_biz_id);
    } if (data.cluster_type === 'tendbcluster') {
      location({
        name: 'tendbClusterInstance',
        query: {
          ip: data.ip,
        },
      }, data.bk_biz_id);
    } else {
      location({
        name: routerNameMap[data.cluster_type],
        query: {
          id: data.id,
        },
      }, data.bk_biz_id);
    }
  };
</script>

