<template>
  <ClusterDetail :cluster-id="clusterId" />
</template>
<script setup lang="ts">
  import { useRoute, useRouter } from 'vue-router';

  import ClusterDetail from '@views/db-manage/mongodb/common/shared-cluster-detail/Index.vue';

  const route = useRoute();
  const router = useRouter();

  const clusterId = Number(route.params.clusterId);

  defineExpose({
    routerBack() {
      router.push({
        name: 'MongoDBSharedClusterList',
      });
    },
  });
</script>
