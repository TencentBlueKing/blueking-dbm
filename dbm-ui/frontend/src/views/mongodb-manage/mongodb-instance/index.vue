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
  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';

  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Detail from './detail/index.vue';
  import List from './list/index.vue';

  const instanceData = ref<{
    instanceAddress: string,
    clusterId: number
  }>();

  const payload = ref();

  const getPayload = (data: MongodbInstanceModel) => {
    payload.value = data;
  };
  </script>

