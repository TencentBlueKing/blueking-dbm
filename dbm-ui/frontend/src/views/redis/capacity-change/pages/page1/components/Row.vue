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
        ref="targetCapacityRef"
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
    <td
      :class="{'shadow-left': isFixed}"
      style="position:sticky;right:0;z-index: 1;background-color: #fff;">
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

  import RenderText from '@components/tools-table-common/RenderText.vue';

  import { AffinityType } from '@views/redis/common/types';

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
    sepcId: number,
    targetShardNum: number;
    targetGroupNum: number;
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
  }

  export interface InfoItem {
    cluster_id: number,
    bk_cloud_id: number,
    db_version: string,
    shard_num: number,
    group_num: number,
    online_switch_type: OnlineSwitchType,
    resource_spec: {
      backend_group: {
        spec_id: number,
        count: number, // 机器组数
        affinity: AffinityType, // 暂时固定 'CROS_SUBZONE',
      }
    }
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    targetCluster: '',
    clusterId: 0,
    bkCloudId: 0,
    sepcId: 0,
    targetShardNum: 0,
    targetGroupNum: 0,
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    versionsMap?: Record<string, string[]>;
    removeable: boolean,
    isFixed?: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
    (e: 'clickSelect'): void
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const versionRef = ref();
  const switchModeRef = ref();
  const targetCapacityRef = ref();

  const versionList = computed(() => {
    if (props.versionsMap && props.data.clusterType) {
      return props.versionsMap[props.data.clusterType].map(item => ({
        id: item,
        name: item,
      }));
    }
    return [];
  });

  const handleClickSelect = () => {
    emits('clickSelect');
  };

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
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
    getValue() {
      return Promise.all([
        versionRef.value.getValue(),
        switchModeRef.value.getValue(),
        targetCapacityRef.value.getValue(),
      ]).then((data) => {
        const [version, switchMode] = data;
        return {
          cluster_id: props.data.clusterId,
          db_version: version,
          bk_cloud_id: props.data.bkCloudId,
          shard_num: props.data.targetShardNum,
          group_num: props.data.targetGroupNum,
          online_switch_type: switchMode,
          resource_spec: {
            backend_group: {
              spec_id: props.data.sepcId,
              count: props.data.targetGroupNum, // 机器组数
              affinity: AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
            },
          },
        };
      });
    },
  });

</script>
<style lang="less" scoped>
.shadow-left {
  &::before {
    position: absolute;
    top: 0;
    left: -10px;
    width: 10px;
    height: 100%;
    background: linear-gradient(to left, rgb(0 0 0 / 12%), transparent);
    content: '';
  }
}

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
