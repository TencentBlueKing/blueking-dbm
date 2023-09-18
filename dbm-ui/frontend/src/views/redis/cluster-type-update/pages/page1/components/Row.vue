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
        ref="clusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.srcClusterType"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderTargetClusterType
        ref="targetClusterTypeRef"
        :exclude-type="props.data.clusterType"
        :is-loading="data.isLoading"
        @change="handleClusterTypeChange" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.currentSepc"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderDeployPlan
        ref="deployPlanRef"
        :data="data.deployPlan"
        :is-loading="data.isLoading"
        :row-data="data"
        :target-cluster-type="selectClusterType" />
    </td>
    <td style="padding: 0;">
      <RenderTargetClusterVersion
        ref="versionRef"
        :data="data.dbVersion"
        :is-loading="data.isLoading"
        :select-list="versionList" />
    </td>
    <td
      style="padding: 0;">
      <RenderText
        :data="data.switchMode"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td :class="{'shadow-column': isFixed}">
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
  import RenderText from '@components/tools-table-common/RenderText.vue';

  import RenderTargetCluster from '@views/redis/common/edit-field/ClusterName.vue';
  import { AffinityType } from '@views/redis/common/types';

  import { random } from '@utils';

  import RenderDeployPlan, { type ExposeValue } from './RenderDeployPlan.vue';
  import RenderTargetClusterType from './RenderTargetClusterType.vue';
  import RenderTargetClusterVersion from './RenderTargetClusterVersion.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    clusterId: number;
    bkCloudId: number;
    switchMode: string;
    currentSepc: string;
    currentSpecId: number;
    dbVersion: string;
    srcClusterType: string;
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
    },
    proxy: {
      id: number;
      count: number;
    },
    targetClusterType?: string;
    currentCapacity?: {
      used: number,
      total: number,
    };
    deployPlan?: {
      used: number;
      current: number;
      total: number;
    },
    backendGroup?: {
      id: number;
      count: number;
    },
    targetShardNum?: number;
  }

  export interface InfoItem {
    src_cluster: number,
    current_cluster_type: string,
    current_shard_num: number,
    current_spec_id: number,
    target_cluster_type: string,
    db_version: string,
    cluster_shard_num: number,
    online_switch_type:'user_confirm',
    resource_spec: {
      proxy: {
        spec_id: number,
        count: number,
        affinity: AffinityType,
      },
      backend_group: {
        spec_id: number,
        count: number, // 机器组数
        affinity: AffinityType,
      },
    }
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    clusterId: 0,
    bkCloudId: 0,
    currentSpecId: 0,
    switchMode: '',
    srcClusterType: '',
    clusterType: '',
    dbVersion: '',
    currentShardNum: 0,
    currentSepc: '',
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
    proxy: {
      id: 0,
      count: 0,
    },
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    clusterTypesMap: Record<string, string[]>;
    inputedClusters?: string[];
    isFixed?: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => ([]),
    isFixed: false,
  });

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const deployPlanRef = ref();
  const targetClusterTypeRef = ref();
  const versionRef = ref();
  const selectClusterType = ref('');

  const versionList = computed(() => {
    if (props.clusterTypesMap && selectClusterType.value in props.clusterTypesMap) {
      return props.clusterTypesMap[selectClusterType.value].map(item => ({
        value: item,
        label: item,
      }));
    }
    return [];
  });

  const handleClusterTypeChange = (value: string) => {
    selectClusterType.value = value;
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
    async getValue() {
      await clusterRef.value.getValue();
      return await Promise.all([
        targetClusterTypeRef.value.getValue(),
        versionRef.value.getValue(),
        deployPlanRef.value.getValue(),
      ]).then((data: [string, string, ExposeValue]) => {
        const [targetClusterType, version, deployData] = data;
        return ({
          src_cluster: props.data.clusterId,
          current_cluster_type: props.data.clusterType,
          current_shard_num: props.data.currentShardNum,
          current_spec_id: props.data.currentSpecId,
          cluster_shard_num: deployData.target_shard_num,
          target_cluster_type: targetClusterType,
          db_version: version,
          online_switch_type: 'user_confirm',
          resource_spec: {
            proxy: {
              spec_id: props.data.proxy.id,
              count: props.data.proxy.count,
              affinity: AffinityType.CROS_SUBZONE,
            },
            backend_group: {
              spec_id: deployData.spec_id,
              count: deployData.count, // 机器组数
              affinity: AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
            },
          },
        });
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
