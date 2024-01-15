<template>
  <div>
    <div
      v-for="item in data"
      :key="item.name"
      class="result-item"
      @click="handleGo(item)">
      <div class="value-text">
        <HightLightText
          :key-word="keyWord"
          :text="item.name" />
        <div class="intro">
          (集群名, {{ item.immute_domain }})
        </div>
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

  import HightLightText from './components/HightLightText.vue';

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
      riak: 'RiakList',
    } as Record<string, string>;

    if (!routerNameMap[data.cluster_type]) {
      return;
    }

    location({
      name: routerNameMap[data.cluster_type],
      query: {
        id: data.id,
      },
    }, data.bk_biz_id);
  };
</script>

