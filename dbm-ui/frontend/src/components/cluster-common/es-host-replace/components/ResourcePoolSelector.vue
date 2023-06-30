<template>
  <div class="es-cluster-replace-resource-pool-selector">
    <BkSelect
      :loading="isResourceSpecLoading"
      :model-value="modelValue.spec_id || undefined"
      @change="handleChange">
      <BkOption
        v-for="item in resourceSpecList?.results"
        :key="item.spec_id"
        :label="item.spec_name"
        :value="item.spec_id" />
    </BkSelect>
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { fetchRecommendSpec } from '@services/dbResource';
  import { getResourceSpecList } from '@services/resourceSpec';

  import type { TReplaceNode } from '../Index.vue';

  interface Props {
    data: TReplaceNode,
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<TReplaceNode['resourceSpec']>({
    required: true,
  });

  const {
    loading: isResourceSpecLoading,
    data: resourceSpecList,
  } = useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: props.data.specClusterType,
        spec_machine_type: props.data.specMachineType,
      },
    ],
  });

  const {
    data: recommendSpecList,
  } = useRequest(fetchRecommendSpec, {
    defaultParams: [
      {
        cluster_id: props.data.clusterId,
        role: props.data.role,
      },
    ],
  });

  const handleChange = (value: number) => {
    modelValue.value = {
      spec_id: value,
      count: props.data.nodeList.length,
      instance_num: 1,
    };
  };

  console.log('recommendSpecList = ', recommendSpecList);
</script>
<style lang="less" scoped>
  .es-cluster-replace-resource-pool-selector {
    position: absolute;
    inset: 43px 0 1px 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
