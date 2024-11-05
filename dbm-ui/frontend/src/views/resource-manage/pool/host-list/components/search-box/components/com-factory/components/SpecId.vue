<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkLoading :loading="isResourceSpecLoading">
    <BkComposeFormItem class="search-spec-id">
      <BkSelect
        v-model="currentDbType"
        :clearable="false"
        :disabled="isDbTypeDisabled"
        filterable
        :input-search="false"
        style="width: 150px"
        @change="handleClusterChange">
        <BkOption
          v-for="item in Object.values(DBTypeInfos)"
          :key="item.id"
          :label="item.name"
          :value="item.id" />
      </BkSelect>
      <BkSelect
        :key="currentDbType"
        v-model="currentMachine"
        :clearable="false"
        :disabled="!currentDbType"
        filterable
        :input-search="false"
        style="width: 150px">
        <BkOption
          v-for="item in clusterMachineList"
          :key="item.value"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
      <BkSelect
        :key="currentMachine"
        :disabled="!currentMachine"
        filterable
        :input-search="false"
        :loading="isResourceSpecListLoading"
        :model-value="defaultValue"
        :placeholder="t('请选择匹配规格')"
        @change="handleChange">
        <BkOption
          v-for="item in resourceSpecList?.results"
          :key="item.spec_id"
          :label="item.spec_name"
          :value="item.spec_id" />
      </BkSelect>
    </BkComposeFormItem>
  </BkLoading>
</template>
<script setup lang="ts">
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceSpec, getResourceSpecList } from '@services/source/dbresourceSpec';

  import { DBTypeInfos, DBTypes, type InfoItem } from '@common/const';

  interface Props {
    model: Record<string, any>;
  }

  interface Emits {
    (e: 'change', value: ValueType): void;
  }

  interface Expose {
    reset: () => void;
  }

  type ValueType = number | string;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

  const defaultValue = defineModel<ValueType>('defaultValue');

  const { t } = useI18n();

  // 临时修复 bk-select 无法重置的问题
  const rerenderKey = ref(0);

  const currentDbType = ref('');
  const currentMachine = ref('');
  const clusterMachineList = shallowRef<InfoItem['machineList']>([]);

  const isDbTypeDisabled = computed(() => props.model.resource_type && props.model.resource_type !== 'PUBLIC');

  const { loading: isResourceSpecLoading, run: fetchResourceSpecDetail } = useRequest(getResourceSpec, {
    manual: true,
    onSuccess(data) {
      const { spec_cluster_type: clusterType, spec_machine_type: machineType } = data;
      currentDbType.value = clusterType;
      currentMachine.value = machineType;
      clusterMachineList.value = DBTypeInfos[clusterType as unknown as DBTypes]?.machineList || [];
    },
  });

  const {
    loading: isResourceSpecListLoading,
    data: resourceSpecList,
    run: fetchResourceSpecList,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  watch(
    defaultValue,
    () => {
      if (defaultValue.value) {
        // 通过规格ID获取规格详情
        fetchResourceSpecDetail({
          spec_id: defaultValue.value as number,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    currentMachine,
    () => {
      if (currentMachine.value) {
        fetchResourceSpecList({
          spec_cluster_type: currentDbType.value,
          spec_machine_type: currentMachine.value,
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.model,
    () => {
      const dbType = props.model.resource_type;
      if (dbType && currentDbType.value && dbType !== currentDbType.value && dbType !== 'PUBLIC') {
        currentDbType.value = dbType;
        clusterMachineList.value = DBTypeInfos[dbType as DBTypes]?.machineList || [];
        currentMachine.value = '';
        defaultValue.value = '';
        return;
      }
      defaultValue.value = props.model.spec_id;
    },
    {
      immediate: true,
    },
  );

  const handleClusterChange = (value: DBTypes) => {
    clusterMachineList.value = DBTypeInfos[value]?.machineList || [];
    currentMachine.value = '';
    defaultValue.value = '';
  };

  const handleChange = (value: ValueType) => {
    defaultValue.value = value;
    emits('change', value);
  };

  defineExpose<Expose>({
    reset() {
      rerenderKey.value = Date.now();
      currentDbType.value = '';
      currentMachine.value = '';
      clusterMachineList.value = [];
    },
  });
</script>
<style lang="less" scoped>
  .search-spec-id {
    display: flex;
    width: 100%;

    :deep(.bk-compose-form-item-tail) {
      flex: 1;
    }
  }
</style>
