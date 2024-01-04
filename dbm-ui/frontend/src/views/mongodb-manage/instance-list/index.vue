<template>
  <StretchLayout
    :min-left-width="368"
    name="instanceViewList">
    <template #list>
      <List
        v-model:instanceData="instanceData"
        @get-payload="getPayload" />
    </template>
    <template
      v-if="instanceData"
      #right>
      <Detail
        :instance-data="instanceData"
        :payload="payload" />
    </template>
  </StretchLayout>
</template>

  <script setup lang="ts">
  import type { PayloadType } from '@services/source/instanceview';

  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Detail from './detail/index.vue';
  import List from './list/index.vue';

  const instanceData = ref<{instanceAddress:string, clusterId:number}>();
  const payload = ref<PayloadType>({
    conf_type: '',
    level_name: '',
    level_value: 0,
    meta_cluster_type: '',
    version: '',
  });

  const getPayload = (data:PayloadType) => {
    payload.value = data;
  };
  </script>
