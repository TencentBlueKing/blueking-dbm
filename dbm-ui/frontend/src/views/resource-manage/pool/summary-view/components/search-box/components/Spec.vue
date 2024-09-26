<template>
  <BkComposeFormItem class="search-box-select-spec">
    <BkSelect
      v-model="clusterType"
      style="width: 150px"
      @change="handleChangeCluster">
      <BkOption
        v-for="item in clusterTypeList"
        :key="item.id"
        :label="item.name"
        :value="item.id" />
    </BkSelect>
    <BkSelect
      :key="clusterType"
      v-model="machineType"
      :disabled="!clusterType"
      style="width: 150px"
      @change="handleChangeMachine">
      <BkOption
        v-for="item in clusterMachineList"
        :key="item.id"
        :label="item.name"
        :value="item.id" />
    </BkSelect>
    <BkSelect
      :key="machineType"
      v-model:model-value="specIdList"
      collapse-tags
      :disabled="!machineType"
      :loading="isLoading"
      multiple
      multiple-mode="tag"
      show-select-all
      @change="handleChange">
      <BkOption
        v-for="item in resourceSpecList?.results"
        :key="item.spec_id"
        :label="item.spec_name"
        :value="`${item.spec_id}`" />
    </BkSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { type ClusterTypeInfoItem, clusterTypeInfos, ClusterTypes } from '@common/const';

  interface Props {
    model: Record<string, string>;
  }

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      cluster_type: string;
      machine_type: string;
      spec_id_list: string;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterType = ref('');
  const machineType = ref('');
  const specIdList = ref<string[]>([]);
  const clusterMachineList = ref<ClusterTypeInfoItem['machineList']>([]);

  const clusterTypeList = computed(
    () => Object.values(clusterTypeInfos).filter((item) => item.dbType === props.model.db_type) || [],
  );

  const {
    loading: isLoading,
    data: resourceSpecList,
    run: fetchResourceSpecList,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  watch(
    () => props.model,
    () => {
      if (props.model.cluster_type) {
        clusterType.value = props.model.cluster_type;
        clusterMachineList.value = clusterTypeInfos[props.model.cluster_type as ClusterTypes]?.machineList || [];
      }
      if (props.model.machine_type) {
        machineType.value = props.model.machine_type;
        fetchResourceSpecList({
          spec_cluster_type: clusterType.value,
          spec_machine_type: props.model.machine_type,
          limit: -1,
        });
      }
      if (props.model.spec_id_list) {
        specIdList.value = props.model.spec_id_list.split(',');
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    specIdList.value = value;
    emits('change');
  };

  const handleChangeMachine = (value: string) => {
    machineType.value = value;
    fetchResourceSpecList({
      spec_cluster_type: clusterType.value,
      spec_machine_type: value,
      limit: -1,
    });
    handleChange([]);
  };

  const handleChangeCluster = (value: string) => {
    clusterMachineList.value = clusterTypeInfos[value as ClusterTypes]?.machineList || [];
    clusterType.value = value;
    handleChangeMachine('');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      cluster_type: clusterType.value,
      machine_type: machineType.value,
      spec_id_list: specIdList.value.join(','),
    }),
  });
</script>

<style lang="less" scoped>
  .search-box-select-spec {
    display: flex;
    width: 100%;

    :deep(.bk-compose-form-item-tail) {
      flex: 1;
    }
  }
</style>
