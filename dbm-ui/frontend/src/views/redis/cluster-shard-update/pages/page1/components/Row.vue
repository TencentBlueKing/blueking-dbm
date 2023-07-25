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
        :data="data.srcCluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.currentCapacity"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderDeployPlan
        :data="data.deployPlan"
        :is-loading="data.isLoading"
        @click-select="handleClickSelect" />
    </td>
    <td
      style="padding: 0;">
      <RenderText
        :data="data.switchMode"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
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
  import RenderText from '@components/db-table-columns/RenderText.vue';

  import { random } from '@utils';

  import RenderDeployPlan from './RenderDeployPlan.vue';
  import RenderTargetCluster from './RenderTargetCluster.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    clusterId: number;
    bkCloudId: number;
    switchMode: string;
    clusterCapacity: number;
    clusterType: string;
    currentShardNum: number;
    specConfig: {
      cpu: {
        max: number;
        min: number;
      },
      id: number;
      mem: {
        max: number;
        min: number;
      },
      qps: {
        max: number;
        min: number;
      },
    };
    currentCapacity?: string;
    deployPlan?: {
      used: number;
      current: number;
      total: number;
    };
    proxy?: {
      id: number;
      count: number;
    },
    backendGroup?: {
      id: number;
      count: number;
    },
    targetShardNum?: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    clusterId: 0,
    bkCloudId: 0,
    switchMode: '',
    clusterCapacity: 0,
    clusterType: '',
    currentShardNum: 0,
    specConfig: {
      cpu: {
        max: 0,
        min: 0,
      },
      id: 0,
      mem: {
        max: 0,
        min: 0,
      },
      qps: {
        max: 0,
        min: 0,
      },
    },
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
    (e: 'clickSelect'): void
  }


  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();


  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleClickSelect = () => {
    emits('clickSelect');
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

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
