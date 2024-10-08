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
        v-model="currentCluster"
        :clearable="false"
        filterable
        :input-search="false"
        style="width: 150px"
        @change="handleClusterChange">
        <BkOption
          v-for="item in Object.values(clusterTypeInfos)"
          :key="item.id"
          :label="item.name"
          :value="item.id" />
      </BkSelect>
      <BkSelect
        :key="currentCluster"
        v-model="currentMachine"
        :clearable="false"
        :disabled="!currentCluster"
        filterable
        :input-search="false"
        style="width: 150px">
        <BkOption
          v-for="item in clusterMachineList"
          :key="item.id"
          :label="item.name"
          :value="item.id" />
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

  import { type ClusterTypeInfoItem, clusterTypeInfos, ClusterTypes } from '@common/const';

  interface Props {
    defaultValue?: number | string;
  }

  interface Emits {
    (e: 'change', value: Props['defaultValue']): void;
  }

  interface Expose {
    reset: () => void;
  }

  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

  const defaultValue = defineModel<Props['defaultValue']>('defaultValue');

  const { t } = useI18n();

  // 临时修复 bk-select 无法重置的问题
  const rerenderKey = ref(0);

  const currentCluster = ref('');
  const currentMachine = ref('');
  const clusterMachineList = shallowRef<ClusterTypeInfoItem['machineList']>([]);

  const { loading: isResourceSpecLoading, run: fetchResourceSpecDetail } = useRequest(getResourceSpec, {
    manual: true,
    onSuccess(data) {
      const { spec_cluster_type: clusterType, spec_machine_type: machineType } = data;
      currentCluster.value = clusterType;
      currentMachine.value = machineType;
      clusterMachineList.value = clusterTypeInfos[clusterType]?.machineList || [];
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
          spec_cluster_type: currentCluster.value,
          spec_machine_type: currentMachine.value,
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleClusterChange = (value: ClusterTypes) => {
    clusterMachineList.value = clusterTypeInfos[value]?.machineList || [];
    currentMachine.value = '';
    defaultValue.value = '';
  };

  const handleChange = (value: Props['defaultValue']) => {
    defaultValue.value = value;
    emits('change', value);
  };

  defineExpose<Expose>({
    reset() {
      rerenderKey.value = Date.now();
      (currentCluster.value = ''), (currentMachine.value = '');
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
