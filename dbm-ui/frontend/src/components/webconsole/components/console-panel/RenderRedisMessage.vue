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
  // 集群所选的数据库编号
  export const clusterSelectedDbIndex: Record<number, number> = {};

  // cmd前缀
  export const getInputPlaceholder = (clusterId: number, domain: string) =>
    clusterSelectedDbIndex[clusterId] ? `${domain}[${clusterSelectedDbIndex[clusterId]}] > ` : `${domain} > `;

  // db独有参数
  export const getDbOwnParams = (clusterId: number, cmd: string) => {
    if (cmd.includes('select')) {
      clusterSelectedDbIndex[clusterId] = Number(cmd.substring('select '.length)) as number;
      return {
        db_num: clusterSelectedDbIndex[clusterId],
      };
    }
    return {};
  };
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const rows = computed(() => props.data.split('\n') || []);
</script>
