<template>
  <BkComposeFormItem class="search-box-select-spec">
    <BkSelect
      v-model="dbType"
      :disabled="isDbTypeDisabled"
      style="width: 150px"
      @change="handleChangeCluster">
      <BkOption
        v-for="item in DBTypeInfos"
        :key="item.id"
        :label="item.name"
        :value="item.id" />
    </BkSelect>
    <BkSelect
      :key="dbType"
      v-model="machineType"
      :disabled="!dbType"
      style="width: 150px"
      @change="handleChangeMachine">
      <BkOption
        v-for="item in clusterMachineList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </BkSelect>
    <BkSelect
      :key="machineType"
      v-model="specIdList"
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

  import { DBTypeInfos, DBTypes, type InfoItem } from '@common/const';

  interface Props {
    model: Record<string, string>;
  }

  interface Emits {
    (
      e: 'change',
      value: {
        cluster_type: string;
        machine_type: string;
        spec_id_list: string;
      },
    ): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const dbType = ref('');
  const machineType = ref('');
  const specIdList = ref<string[]>([]);
  const clusterMachineList = ref<InfoItem['machineList']>([]);

  const isDbTypeDisabled = computed(() => !!props.model.db_type && props.model.db_type !== 'PUBLIC');

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
      const modelDbType = props.model.db_type;
      if (!props.model.spec_id_list) {
        specIdList.value = [];
      }
      dbType.value = props.model.cluster_type || '';
      machineType.value = props.model.machine_type || '';
      clusterMachineList.value = dbType.value ? DBTypeInfos[dbType.value as DBTypes]?.machineList || [] : [];
      if (modelDbType && modelDbType !== dbType.value && modelDbType !== 'PUBLIC') {
        dbType.value = modelDbType;
        machineType.value = '';
        specIdList.value = [];
        return;
      }

      if (props.model.machine_type) {
        machineType.value = props.model.machine_type;
        fetchResourceSpecList({
          spec_cluster_type: dbType.value,
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
    emits('change', {
      cluster_type: dbType.value,
      machine_type: machineType.value,
      spec_id_list: specIdList.value.join(','),
    });
  };

  const handleChangeMachine = (value: string) => {
    machineType.value = value;
    fetchResourceSpecList({
      spec_cluster_type: dbType.value,
      spec_machine_type: value,
      limit: -1,
    });
    handleChange([]);
  };

  const handleChangeCluster = (value: DBTypes) => {
    clusterMachineList.value = DBTypeInfos[value]?.machineList || [];
    dbType.value = value;
    handleChangeMachine('');
  };
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
