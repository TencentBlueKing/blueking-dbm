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
    :label="label"
    :min-width="minWidth"
    required
    :rule="rules">
    <EditableSelect
      v-model="modelValue"
      :list="selectList"
      @change="handleSelectChange">
      <template #option="{ item }">
        <div class="spec-display">
          {{ item.label }}
          <span class="spec-display-count">{{ countMap[item.value] }}</span>
        </div>
      </template>
      <template #trigger>
        <EditableInput
          v-if="modelValue === HostSelectType.MANUAL"
          v-model="localValue"
          :placeholder="t('请选择主机')">
          <template #default>
            <span ref="rootRef">{{ localValue }}</span>
          </template>
          <template #append>
            <DbIcon
              v-bk-tooltips="t('从资源池选择')"
              class="select-icon"
              type="host-select"
              @click.stop="handleShowSelector" />
          </template>
        </EditableInput>
        <div
          v-else-if="modelValue === HostSelectType.AUTO"
          class="table-cell">
          {{ t('自动匹配') }}
        </div>
        <div
          v-else
          class="table-cell placeholder-text">
          {{ t(placeholder) }}
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
  <ResourceHostSelector
    v-model:is-show="showSelector"
    v-mode="hostList"
    :limit="limit"
    :params="params"
    @change="handleSelectorChange" />
</template>

<script lang="ts">
  export enum HostSelectType {
    AUTO = 'auto',
    MANUAL = 'manual',
  }
</script>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface IHost {
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
  }

  interface Props {
    bkCloudId?: number;
    field: string; // 绑选项值的vmodel，不绑主机列表
    label: string;
    limit: number;
    minWidth?: number;
    params?: ComponentProps<typeof ResourceHostSelector>['params'];
    placeholder?: string;
    specIds?: number[];
  }

  type Emits = (e: 'change', list: IHost[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    bkCloudId: 0,
    minWidth: 300,
    params: () => ({}),
    placeholder: '请选择',
    specIds: () => [],
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const hostList = ref<IHost[]>([]);
  const localValue = ref('');

  const countMap = reactive<Record<string, number>>({
    [HostSelectType.AUTO]: 0,
    [HostSelectType.MANUAL]: 0,
  });

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
      message: t('请选择节点类型'),
      validator: (value: HostSelectType) => Boolean(value),
    },
    {
      message: t('请选择主机'),
      validator: (value: HostSelectType) => {
        if (value === HostSelectType.AUTO) {
          return true;
        }
        return Boolean(localValue.value);
      },
    },
  ];

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(countResult) {
      countMap[HostSelectType.AUTO] = Object.values(countResult).reduce<number>((acc, cur) => acc + cur, 0);
    },
  });

  watch(
    () => props.specIds,
    () => {
      if (props.specIds.length) {
        fetchSpecResourceCount({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: props.bkCloudId,
          spec_ids: props.specIds,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (data: IValue[]) => {
    hostList.value = data.map((item) => ({
      bk_biz_id: item.dedicated_biz || item.bk_biz_id,
      bk_cloud_id: item.bk_cloud_id,
      bk_host_id: item.bk_host_id,
      ip: item.ip,
    }));
    localValue.value = data.map((item) => item.ip).join(',');
    emits('change', hostList.value);
  };

  const handleSelectChange = () => {
    handleSelectorChange([]);
  };
</script>

<style lang="less" scoped>
  .table-cell {
    flex: 1;
    padding: 0 8px;
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

  .spec-display {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .spec-display-count {
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
