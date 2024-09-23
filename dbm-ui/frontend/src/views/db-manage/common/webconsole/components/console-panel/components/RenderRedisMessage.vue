<template>
  <p
    v-for="(row, index) in rows"
    :key="index"
    class="preserve-whitespace">
    {{ row }}
  </p>
</template>
<script lang="ts">
  interface Props {
    data: string;
  }

  // 集群所选的数据库索引
  const clusterSelectedDbIndex: Record<number, number> = {};

  // 设置当前集群id所选数据库索引
  const setDbIndexByClusterId = (clusterId: number, value = 0) => {
    clusterSelectedDbIndex[clusterId] = value;
  };

  // 命令行前缀
  export const getInputPlaceholder = (clusterId: number, domain: string) => {
    clusterSelectedDbIndex[clusterId] ??= 0;
    return `${domain}[${clusterSelectedDbIndex[clusterId]}] > `;
  };

  // 切换数据库索引
  export const switchDbIndex = ({
    clusterId,
    cmd,
    queryResult,
    commandInputs,
  }: {
    clusterId: number;
    cmd: string;
    queryResult: string;
    commandInputs: string[];
  }) => {
    if (/select/i.test(cmd) && queryResult === 'OK') {
      const newDbIndex = Number(cmd.substring('select '.length));
      setDbIndexByClusterId(clusterId, newDbIndex);
      const newCommandInputs = commandInputs.map((item) => item.replace(/\[(\d+)\]/, `[${newDbIndex}]`));
      return {
        dbIndex: newDbIndex,
        commandInputs: newCommandInputs,
      };
    }
    return {
      dbIndex: clusterSelectedDbIndex[clusterId],
      commandInputs,
    };
  };
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const rows = computed(() => props.data.split('\n') || []);
</script>

<style lang="less" scoped>
  .preserve-whitespace {
    font-family: 'Courier New', Courier, monospace; /* 等宽字体 */
    white-space: pre;
  }
</style>
