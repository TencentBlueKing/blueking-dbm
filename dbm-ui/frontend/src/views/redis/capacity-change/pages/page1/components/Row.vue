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
  <tr>
    <td style="padding: 0;">
      <RenderTargetCluster
        :model-value="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderCurrentSpec
        :data="data.currentPlan"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0;">
      <RenderCurrentSpec
        :data="data.currentPlan"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0;">
      <RenderCurrentSpec
        :data="data.currentPlan"
        :is-loading="data.isLoading" />
    </td>
    <td
      style="padding: 0;">
      <RenderCurrentCapacity
        :data="data.currentCapacity"
        :is-loading="data.isLoading" />
    </td>
    <td
      style="padding: 0;">
      <RenderTargetCapacity
        ref="scaleUpPlanRef"
        :data="data.scaleUpPlan"
        :is-loading="data.isLoading"
        @click-select="handleClickSelect" />
    </td>
    <td
      style="padding: 0;">
      <RenderSpecifyVersion
        ref="versionRef"
        :data="data.version"
        :is-loading="data.isLoading"
        :list="versionList" />
    </td>
    <td>
      <div class="action-box">
        <div
          class="action-btn"
          @click="handleAppend">
          <DbIcon type="plus-fill" />
        </div>
        <div
          class="action-btn"
          :class="{
            disabled: removeable
          }"
          @click="handleRemove">
          <DbIcon type="minus-fill" />
        </div>
      </div>
    </td>
  </tr>
</template>
<script lang="ts">
  import { ref } from 'vue';

  import { random } from '@utils';

  import RenderCurrentCapacity from './RenderCurrentCapacity.vue';
  import RenderCurrentSpec from './RenderCurrentSpec.vue';
  import RenderSpecifyVersion from './RenderSpecifyVersion.vue';
  import RenderTargetCapacity from './RenderTargetCapacity.vue';
  import RenderTargetCluster from './RenderTargetCluster.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    currentPlan: string;
    scaleUpPlan?: string;
    currentCapacity?: string;
    estimateCapacity?: string;
    version?: string;
  }

  // 创建表格数据
  export const createRowData = () => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    currentPlan: '',
    scaleUpPlan: '',
    currentCapacity: '',
    estimateCapacity: '',
    version: '',

  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    versionList?: {
      id: string;
      name: string
    }[];
    removeable: boolean,
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'onClusterInputFinish', value: string): void
    (e: 'click-select'): void
  }

  interface Exposes {
    getValue: () => Promise<{
      scaleUpPlan: string;
      version: string;
    }>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const scaleUpPlanRef = ref();
  const versionRef = ref();

  const handleClickSelect  = () => {
    emits('click-select');
  };

  const handleInputFinish = (value: string) => {
    emits('onClusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    async getValue() {
      return Promise.all([
        scaleUpPlanRef.value.getValue(),
        versionRef.value.getValue(),
      ]).then((data) => {
        const [scaleUpPlan, version] = data;
        return {
          scaleUpPlan,
          version,
        };
      });
    },
  });

</script>
<style lang="less" scoped>
  .action-box {
    display: flex;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
