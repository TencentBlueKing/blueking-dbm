<template>
  <p
    v-for="(row, index) in rows"
    :key="index">
    <span>{{ row }}</span>
  </p>
</template>
<script lang="ts">
  export interface Props {
    data: string;
  }
  // 集群所选的数据库索引
  export const clusterSelectedDbIndex: Record<number, number> = {};

  // 设置当前集群id所选数据库索引
  export const setDbIndexByClusterId = (clusterId: number, value = 0) => {
    clusterSelectedDbIndex[clusterId] = value;
  };

  // cmd前缀
  export const getInputPlaceholder = (clusterId: number, domain: string) => {
    if (!clusterSelectedDbIndex[clusterId]) {
      setDbIndexByClusterId(clusterId);
    }
    return `${domain}[${clusterSelectedDbIndex[clusterId]}] > `;
  };

  // db独有参数
  export const getDbOwnParams = (clusterId: number, cmd: string) => {
    if (cmd.includes('select')) {
      setDbIndexByClusterId(clusterId, Number(cmd.substring('select '.length)) as number);
    }
    return {
      db_num: clusterSelectedDbIndex[clusterId],
    };
  };
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const rows = computed(() => props.data.split('\n') || []);
</script>
