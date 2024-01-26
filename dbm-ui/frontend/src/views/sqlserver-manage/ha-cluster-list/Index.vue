<template>
  <StretchLayout
    :min-left-width="368"
    name="sqlserverHaClusterList">
    <template #list>
      <List v-model:haClusterData="haClusterData" />
    </template>
    <template
      v-if="haClusterData"
      #right>
      <Detail :ha-cluster-data="haClusterData" />
    </template>
  </StretchLayout>
</template>
<script setup lang="ts">
  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Detail from './components/detail/index.vue';
  import List from './components/List.vue';

  const haClusterData = ref<{
    clusterId: number
  }>();
</script>
