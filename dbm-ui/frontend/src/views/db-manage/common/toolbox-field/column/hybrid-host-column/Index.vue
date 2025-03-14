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
  <EditableColumn
    :field="field"
    :label="t(label)"
    :min-width="minWidth"
    required
    :rules="selectMethod === SELECT_METHODS.MANUAL ? rules : []">
    <EditableSelect
      v-model="selectMethod"
      :list="selectList"
      @change="handleSelectChange">
      <template #option="{ item }">
        <div class="flex-center">
          {{ item.label }}
          <span class="flex-center-count">{{ count }}</span>
        </div>
      </template>
      <template #trigger>
        <div
          v-if="selectMethod === SELECT_METHODS.MANUAL"
          class="table-cell">
          <EditableTagInput
            v-model="renderText"
            :placeholder="t('请选择主机')"
            @remove="handleRemove"
            @remove-all="handleRemoveAll" />
          <DbIcon
            class="select-icon"
            type="host-select"
            @click.stop="handleShowSelector" />
        </div>
        <div
          v-else-if="selectMethod === SELECT_METHODS.AUTO"
          class="table-cell pl-8">
          {{ t('自动匹配') }}
        </div>
        <div
          v-else
          class="table-cell pl-8 placeholder-text">
          {{ t(placeholder) }}
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[clusterType]"
    :selected="selected"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>

<script lang="ts">
  export enum SELECT_METHODS {
    AUTO = 'auto',
    MANUAL = 'manual',
  }
</script>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType as InstanceSelectorPanelListType,
  } from '@components/instance-selector/Index.vue';

  export type PanelListType = InstanceSelectorPanelListType;

  interface Props {
    clusterType: ClusterTypes | 'TendbClusterHost' | 'mongoCluster';
    count: number;
    field: string;
    label?: string;
    minWidth?: number;
    placeholder?: string;
    tabListConfig?: ComponentProps<typeof InstanceSelector>['tabListConfig'];
  }

  const props = withDefaults(defineProps<Props>(), {
    label: '主机选择方式',
    minWidth: 200,
    placeholder: '请选择',
    tabListConfig: () => ({}),
  });

  const selectMethod = defineModel<string>('selectMethod', {
    required: true,
  });

  const hostList = defineModel<
    {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      instance_address?: string;
      ip: string;
    }[]
  >('hostList', {
    required: true,
  });

  const { t } = useI18n();

  const isShowSelector = ref(false);
  const selected = shallowRef<InstanceSelectorValues<IValue>>({});
  const firsrColumnKey = computed<'ip' | 'instance_address'>(() => props.tabListConfig?.firsrColumn?.field || 'ip');
  const renderText = computed(() => hostList.value.map((item) => item[firsrColumnKey.value] as string));

  const selectList = [
    {
      label: t('自动匹配'),
      value: SELECT_METHODS.AUTO,
    },
    {
      label: t('手动选择'),
      value: SELECT_METHODS.MANUAL,
    },
  ];

  const rules = [
    {
      message: t('请选择主机'),
      trigger: 'blur',
      validator: () => hostList.value.length > 0,
    },
  ];

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const updateHostList = () => {
    hostList.value = selected.value[props.clusterType].map((item) => {
      const base: (typeof hostList.value)[0] = {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
      };
      if (firsrColumnKey.value === 'instance_address') {
        base.instance_address = item.instance_address;
      }
      return base;
    });
  };

  const handleRemoveAll = () => {
    selected.value[props.clusterType] = [];
    updateHostList();
  };

  const handleSelectorChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    selected.value = selectedValues;
    updateHostList();
    isShowSelector.value = false;
  };

  const handleRemove = (removeItem: { id: string; name: string }) => {
    const removeIndex = selected.value[props.clusterType].findIndex(
      (item) => item[firsrColumnKey.value] === removeItem.id,
    );
    selected.value[props.clusterType].splice(removeIndex, 1);
    updateHostList();
  };

  const handleSelectChange = (value: string) => {
    if (value === SELECT_METHODS.MANUAL) {
      isShowSelector.value = true;
    } else {
      selected.value[props.clusterType] = [];
      updateHostList();
    }
  };
</script>

<style lang="less" scoped>
  .table-cell {
    display: flex;
    align-items: center;
    min-height: 40px;
  }

  .select-icon {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }

  .flex-center {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .flex-center-count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: #979ba5;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }

  .placeholder-text {
    color: rgb(99 101 110 / 50%);
  }
</style>
