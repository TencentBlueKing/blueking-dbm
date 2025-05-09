<template>
  <ClusterDetail :cluster-id="clusterId" />
</template>
<script setup lang="ts">
  import { useRoute, useRouter } from 'vue-router';

  import ClusterDetail from '@views/db-manage/mysql/common/cluster-detail/Index.vue';

  const route = useRoute();
  const router = useRouter();

  const clusterId = Number(route.params.clusterId);

  defineExpose({
    routerBack() {
      if (route.name === 'tendbsingleDetail') {
        router.push({
          name: 'DatabaseTendbsingle',
        });
      } else {
        router.push({
          name: 'DatabaseTendbha',
        });
      }
    },
  });
</script>
