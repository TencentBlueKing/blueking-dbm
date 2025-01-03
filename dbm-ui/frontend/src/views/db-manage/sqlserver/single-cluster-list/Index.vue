<template>
  <StretchLayout
    :left-width="368"
    name="sqlserverSingleClusterList">
    <template #list>
      <List v-model:single-cluster-data="singleClusterData" />
    </template>
    <template
      v-if="singleClusterData"
      #right>
      <Detail :single-cluster-data="singleClusterData" />
    </template>
  </StretchLayout>
</template>
<script setup lang="ts">
  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Detail from './components/detail/index.vue';
  import List from './components/List.vue';

  const singleClusterData = ref<{ clusterId: number }>();
</script>
