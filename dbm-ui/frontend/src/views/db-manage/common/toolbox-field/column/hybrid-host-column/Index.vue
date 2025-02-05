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
    :rule="rules">
    <EditableSelect
      v-model="selectType"
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
          v-if="selectType === HostSelectType.MANUAL"
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
          v-else-if="selectType === HostSelectType.AUTO"
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
    v-if="selectType === HostSelectType.MANUAL"
    v-model:is-show="showSelector"
    :cluster-types="clusterTypes"
    :selected="selected"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>

<script lang="ts">
  export enum HostSelectType {
    AUTO = 'auto',
    MANUAL = 'manual',
  }
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';

  interface Props {
    field: string; // 主机选择方式
    label?: string;
    minWidth?: number;
    placeholder?: string;
    clusterTypes: (ClusterTypes | 'TendbClusterHost' | 'mongoCluster')[];
    tabListConfig: ComponentProps<typeof InstanceSelector>['tabListConfig'];
    count: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    label: '主机选择方式',
    minWidth: 200,
    placeholder: '请选择',
  });

  const { t } = useI18n();

  const selectType = defineModel<string>('type', {
    default: '',
  });

  const hostList = defineModel<
    {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      instance_address?: string;
    }[]
  >('list', {
    default: () => [],
  });

  const showSelector = ref(false);
  const selected = shallowRef<InstanceSelectorValues<IValue>>({});
  const firsrColumnKey = computed<'ip' | 'instance_address'>(() => props.tabListConfig?.firsrColumn?.field || 'ip');
  const renderText = computed(() => hostList.value.map((item) => item[firsrColumnKey.value] as string));

  const selectList = [
    {
      label: t('自动匹配'),
      value: HostSelectType.AUTO,
    },
    {
      label: t('手动选择'),
      value: HostSelectType.MANUAL,
    },
  ];

  const rules = [
    {
      validator: (value: HostSelectType) => Boolean(value),
      message: t('请选择节点类型'),
    },
    {
      validator: (value: HostSelectType) => {
        if (value === HostSelectType.AUTO) {
          return true;
        }
        return Boolean(renderText.value);
      },
      message: t('请选择主机'),
    },
  ];

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleRemoveAll = () => {
    hostList.value = [];
    props.clusterTypes.forEach((clusterType) => {
      selected.value[clusterType] = [];
    });
  };

  const handleRemove = (removeItem: { id: string; name: string }) => {
    const removeIndex = hostList.value.findIndex((item) => item[firsrColumnKey.value] === removeItem.id);
    hostList.value.splice(removeIndex, 1);
    props.clusterTypes.forEach((clusterType) => {
      const removeIndex = selected.value[clusterType].findIndex((item) => item[firsrColumnKey.value] === removeItem.id);
      selected.value[clusterType].splice(removeIndex, 1);
    });
  };

  const handleSelectorChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    selected.value = selectedValues;
    hostList.value = _.flatten(Object.values(selectedValues)).map((item) => {
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

  const handleSelectChange = () => {
    handleSelectorChange({});
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
