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
      :loading="isResourceSpecListLoading"
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

  import { type ClusterTypeInfoItem, clusterTypeInfos, ClusterTypes, DBTypes, MachineTypes } from '@common/const';

  import { getResourceSpecList } from '@/services/source/dbresourceSpec';

  interface Props {
    dbType: DBTypes;
  }

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      spec_param: {
        db_type: DBTypes;
        machine_type: MachineTypes;
        cluster_type: ClusterTypes;
        spec_id_list: number[];
      };
    };
    reset: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const emits = defineEmits<Emits>();

  const currentCluster = ref('');
  const currentMachine = ref('');
  const currentSpecIdList = ref<number[]>([]);
  const clusterMachineList = ref<ClusterTypeInfoItem['machineList']>([]);

  const currentClusterList = computed(
    () => Object.values(clusterTypeInfos).filter((item) => item.dbType === props.dbType) || [],
  );

  const {
    loading: isResourceSpecListLoading,
    data: resourceSpecList,
    run: fetchResourceSpecList,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  const reset = () => {
    currentCluster.value = '';
    currentMachine.value = '';
    currentSpecIdList.value = [];
  };

  watch(
    () => props.dbType,
    () => {
      reset();
    },
  );

  const handleChangeCluster = (value: ClusterTypes) => {
    clusterMachineList.value = clusterTypeInfos[value]?.machineList || [];
    emits('change');
  };

  const handleChangeMachine = (value: MachineTypes) => {
    fetchResourceSpecList({
      spec_cluster_type: currentCluster.value,
      spec_machine_type: value,
      limit: -1,
    });
    emits('change');
  };

  const handleChange = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      spec_param: {
        db_type: props.dbType as DBTypes,
        machine_type: currentMachine.value as MachineTypes,
        cluster_type: currentCluster.value as ClusterTypes,
        spec_id_list: currentSpecIdList.value as number[],
      },
    }),
    reset,
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
