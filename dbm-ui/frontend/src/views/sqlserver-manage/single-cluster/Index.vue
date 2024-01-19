<template>
  <StretchLayout
    :min-left-width="368"
    name="sqlserverClusterSingleList">
    <template #list>
      <List v-model:singleClusterData="singleClusterData" />
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

  const singleClusterData = ref<{
    clusterId:number
  }>();
</script>
