<template>
  <StretchLayout
    :left-width="368"
    name="sqlserverHaClusterList">
    <template #list>
      <List
        ref="listRef"
        v-model:ha-cluster-data="haClusterData" />
    </template>
    <template
      v-if="haClusterData"
      #right>
      <Detail
        :ha-cluster-data="haClusterData"
        @refresh="handleRefresh" />
    </template>
  </StretchLayout>
</template>
<script setup lang="ts">
  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Detail from './components/detail/index.vue';
  import List from './components/List.vue';

  const listRef = ref<InstanceType<typeof List>>();
  const haClusterData = ref<{ clusterId: number }>();

  const handleRefresh = () => {
    listRef.value!.refresh();
  };
</script>
