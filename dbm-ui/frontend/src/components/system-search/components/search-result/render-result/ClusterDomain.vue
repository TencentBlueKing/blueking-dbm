<template>
  <div>
    <div
      v-for="item in data"
      :key="item.immute_domain"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <HightLightText
          :key-word="keyWord"
          :text="item.immute_domain" />
        <div class="intro">
          (域名)
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
      cluster_type: string,
      id: number,
      immute_domain: string,
      name: string
    }[],
    bizIdNameMap: Record<number, string>
  }

  defineProps<Props>();

  const location = useLocation();

  const handleGo = (data: Props['data'][number]) => {
    console.log(data);
    systemSearchCache.appendItem(data.immute_domain);

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
    } as Record<string, string>;

    if (!routerNameMap[data.cluster_type]) {
      return;
    }

    location({
      name: routerNameMap[data.cluster_type],
      query: {
        id: data.id,
      },
    });
  };
</script>

