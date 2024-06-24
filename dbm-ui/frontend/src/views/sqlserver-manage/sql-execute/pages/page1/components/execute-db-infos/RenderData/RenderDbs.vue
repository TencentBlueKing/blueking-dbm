<template>
  <div v-bkloading="{ isLoading }">asdasd</div>
</template>
<script setup lang="ts">
  import { watch } from 'vue';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  interface Props {
    clusterId: number;
    dbList: string[];
    ignoreDbList: string[];
  }

  const props = defineProps<Props>();

  const { loading: isLoading, run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
  });

  watch(
    () => [props.clusterId, props.dbList, props.ignoreDbList],
    () => {
      if (!props.clusterId || !props.dbList || !props.ignoreDbList) {
        return;
      }
      fetchSqlserverDbs({
        cluster_id: props.clusterId,
        db_list: props.dbList,
        ignore_db_list: props.ignoreDbList,
      });
    },
    {
      immediate: true,
    },
  );
</script>
