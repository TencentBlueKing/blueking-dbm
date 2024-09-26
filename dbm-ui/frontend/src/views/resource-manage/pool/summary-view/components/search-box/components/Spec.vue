<template>
  <BkComposeFormItem class="search-box-select-spec">
    <BkSelect
      v-model="currentCluster"
      style="width: 150px"
      @change="handleChangeCluster">
      <BkOption
        v-for="item in currentClusterList"
        :key="item.id"
        :label="item.name"
        :value="item.id" />
    </BkSelect>
    <BkSelect
      :key="currentCluster"
      v-model="currentMachine"
      :disabled="!currentCluster"
      style="width: 150px"
      @change="handleChangeMachine">
      <BkOption
        v-for="item in clusterMachineList"
        :key="item.id"
        :label="item.name"
        :value="item.id" />
    </BkSelect>
    <BkSelect
      :key="currentMachine"
      v-model:model-value="currentSpecIdList"
      collapse-tags
      :disabled="!currentMachine"
      :loading="isLoading"
      multiple
      multiple-mode="tag"
      show-select-all
      @change="handleChange">
      <BkOption
        v-for="item in resourceSpecList?.results"
        :key="item.spec_id"
        :label="item.spec_name"
        :value="item.spec_id" />
    </BkSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { type ClusterTypeInfoItem, clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import { getResourceSpecList } from '@/services/source/dbresourceSpec';

  interface Props {
    dbType: DBTypes;
  }

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      db_type: string;
      machine_type: string;
      cluster_type: string;
      spec_id_list: string;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const currentCluster = ref('');
  const currentMachine = ref('');
  const currentSpecIdList = ref<number[]>([]);
  const clusterMachineList = ref<ClusterTypeInfoItem['machineList']>([]);

  const currentClusterList = computed(
    () => Object.values(clusterTypeInfos).filter((item) => item.dbType === props.dbType) || [],
  );

  const {
    loading: isLoading,
    data: resourceSpecList,
    run: fetchResourceSpecList,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  watch(
    () => props.dbType,
    () => {
      currentCluster.value = '';
      currentMachine.value = '';
      currentSpecIdList.value = [];
    },
  );

  const handleChange = () => {
    emits('change');
  };

  const handleChangeCluster = (value: string) => {
    clusterMachineList.value = clusterTypeInfos[value as ClusterTypes]?.machineList || [];
    currentMachine.value = '';
    currentSpecIdList.value = [];
    handleChange();
  };

  const handleChangeMachine = (value: string) => {
    currentSpecIdList.value = [];
    fetchResourceSpecList({
      spec_cluster_type: currentCluster.value,
      spec_machine_type: value,
      limit: -1,
    });
    handleChange();
  };

  defineExpose<Exposes>({
    getValue: () => ({
      db_type: props.dbType,
      machine_type: currentMachine.value,
      cluster_type: currentCluster.value,
      spec_id_list: currentSpecIdList.value.join(','),
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
