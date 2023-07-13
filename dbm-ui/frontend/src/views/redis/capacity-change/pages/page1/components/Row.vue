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
        :model-value="data.targetCluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.currentSepc"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.shardNum"
        :is-loading="data.isLoading"
        placeholder="--" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.groupNum"
        :is-loading="data.isLoading"
        placeholder="--" />
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
        :data="data.targetCapacity"
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
    <td
      style="padding: 0;">
      <RenderSwitchMode
        ref="switchModeRef"
        :is-loading="data.isLoading" />
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

  import { RedisClusterTypes } from '@services/model/redis/redis';

  import RenderText from '@components/db-table-columns/RenderText.vue';

  import { random } from '@utils';

  import RenderCurrentCapacity from './RenderCurrentCapacity.vue';
  import RenderSpecifyVersion from './RenderSpecifyVersion.vue';
  import RenderSwitchMode, { type OnlineSwitchType } from './RenderSwitchMode.vue';
  import RenderTargetCapacity from './RenderTargetCapacity.vue';
  import RenderTargetCluster from './RenderTargetCluster.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    targetCluster: string;
    clusterId: number;
    bkCloudId: number;
    shardNum?: number;
    groupNum?: number;
    currentSepc?: string;
    currentCapacity?: {
      used: number,
      total: number,
    };
    targetCapacity?: {
      current: number,
      used: number,
      total: number,
    };
    version?: string;
    clusterType?: RedisClusterTypes;
    switchMode?: OnlineSwitchType;
    sepcId?: number,
    targetShardNum?: number;
    targetGroupNum?: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    targetCluster: '',
    clusterId: 0,
    bkCloudId: 0,
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
      version: string,
      switchMode: string,
    }>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const versionRef = ref();
  const switchModeRef = ref();

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
        versionRef.value.getValue(),
        switchModeRef.value.getValue(),
      ]).then((data) => {
        const [version, switchMode] = data;
        return {
          version,
          switchMode,
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
