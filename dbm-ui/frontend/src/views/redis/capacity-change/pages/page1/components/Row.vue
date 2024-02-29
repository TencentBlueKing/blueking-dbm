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
    <!-- <FixedColumn fixed="left">
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.targetCluster"
        :inputed="inputedClusters"
        @on-input-finish="handleInputFinish" />
    </FixedColumn> -->
    <td style="padding: 0">
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.targetCluster"
        :inputed="inputedClusters"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.currentSepc"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.shardNum"
        :is-loading="data.isLoading"
        placeholder="--" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.groupNum"
        :is-loading="data.isLoading"
        placeholder="--" />
    </td>
    <td style="padding: 0">
      <RenderCurrentCapacity
        :data="data.currentCapacity"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderTargetCapacity
        ref="targetCapacityRef"
        :is-disabled="!data.targetCluster"
        :is-loading="data.isLoading"
        :row-data="data" />
    </td>
    <td style="padding: 0">
      <RenderSpecifyVersion
        ref="versionRef"
        :data="data.version"
        :is-loading="data.isLoading"
        :list="versionList" />
    </td>
    <td style="padding: 0">
      <RenderSwitchMode
        ref="switchModeRef"
        :is-loading="data.isLoading" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { ref } from 'vue';

  import { RedisClusterTypes } from '@services/model/redis/redis';

  // import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/redis/common/edit-field/ClusterName.vue';
  import { AffinityType } from '@views/redis/common/types';

  import { random } from '@utils';

  import RenderCurrentCapacity from './RenderCurrentCapacity.vue';
  import RenderSpecifyVersion from './RenderSpecifyVersion.vue';
  import RenderSwitchMode, { type OnlineSwitchType } from './RenderSwitchMode.vue';
  import RenderTargetCapacity from './RenderTargetCapacity.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    targetCluster: string;
    clusterId: number;
    bkCloudId: number;
    sepcId: number;
    targetShardNum: number;
    targetGroupNum: number;
    shardNum?: number;
    groupNum?: number;
    currentSepc?: string;
    targetCapacity?: {
      current: number;
      used: number;
      total: number;
    };
    currentCapacity?: {
      used: number;
      total: number;
    };
    version?: string;
    clusterType?: RedisClusterTypes;
    switchMode?: OnlineSwitchType;
  }

  export interface InfoItem {
    cluster_id: number;
    bk_cloud_id: number;
    db_version: string;
    shard_num: number;
    group_num: number;
    online_switch_type: OnlineSwitchType;
    capacity: number;
    future_capacity: number;
    resource_spec: {
      backend_group: {
        spec_id: number;
        count: number; // 机器组数
        affinity: AffinityType; // 暂时固定 'CROS_SUBZONE',
      };
    };
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
    data: IDataRow;
    removeable: boolean;
    inputedClusters?: string[];
    versionsMap?: Record<string, string[]>;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
    versionsMap: () => ({}),
  });

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const versionRef = ref();
  const switchModeRef = ref();
  const targetCapacityRef = ref();

  const versionList = computed(() => {
    if (props.versionsMap && props.data.clusterType) {
      return props.versionsMap[props.data.clusterType].map((item) => ({
        value: item,
        label: item,
      }));
    }
    return [];
  });

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    emits('remove');
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value.getValue();
      return Promise.all([
        versionRef.value.getValue(),
        switchModeRef.value.getValue(),
        targetCapacityRef.value.getValue(),
      ]).then((data) => {
        const [version, switchMode, targetCapacity] = data;
        return {
          cluster_id: props.data.clusterId,
          db_version: version,
          bk_cloud_id: props.data.bkCloudId,
          online_switch_type: switchMode,
          ...targetCapacity,
        };
      });
    },
  });
</script>
