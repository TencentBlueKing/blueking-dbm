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
    <td style="padding: 0">
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterTypeName"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.srcClusterType"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderTargetClusterType
        ref="targetClusterTypeRef"
        :data="data.targetClusterType"
        :exclude-type="data.clusterType"
        :is-loading="data.isLoading"
        @change="handleClusterTypeChange" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.currentSepc"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderDeployPlan
        ref="deployPlanRef"
        :is-disabled="!data.srcCluster"
        :is-loading="data.isLoading"
        :row-data="data"
        :target-cluster-type="selectClusterType" />
    </td>
    <td style="padding: 0">
      <RenderTargetClusterVersion
        ref="versionRef"
        :cluster-type="selectClusterType"
        :data="data.dbVersion" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.switchMode"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <OperateColumn
      :removeable="removeable"
      show-clone
      @add="handleAppend"
      @clone="handleClone"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/db-manage/redis/common/edit-field/ClusterName.vue';
  import RenderTargetClusterVersion from '@views/db-manage/redis/common/edit-field/VersionSelect.vue';
  import { AffinityType } from '@views/db-manage/redis/common/types';

  import { random } from '@utils';

  import RenderDeployPlan, { type ExposeValue } from './RenderDeployPlan.vue';
  import RenderTargetClusterType from './RenderTargetClusterType.vue';

  export interface IDataRow {
    bkCloudId: number;
    clusterId: number;
    clusterType: string;
    clusterTypeName: string;
    currentCapacity?: {
      total: number;
      used: number;
    };
    currentSepc: string;
    currentShardNum: number;
    currentSpecId: number;
    dbVersion: string;
    deployPlan?: {
      current: number;
      total: number;
      used: number;
    };
    disasterToleranceLevel: string;
    groupNum: number;
    isLoading: boolean;
    proxy: {
      count: number;
      id: number;
    };
    rowKey: string;
    specConfig: {
      cpu: {
        max: number;
        min: number;
      };
      id: number;
      mem: {
        max: number;
        min: number;
      };
      qps: {
        max: number;
        min: number;
      };
    };
    srcCluster: string;
    srcClusterType: string;
    switchMode: string;
    targetClusterType?: string;
    targetShardNum?: number;
  }

  export type IDataRowBatchKey = keyof Pick<IDataRow, 'dbVersion' | 'switchMode'>;

  export interface InfoItem {
    capacity: number;
    cluster_shard_num: number;
    current_cluster_type: string;
    current_shard_num: number;
    current_spec_id: number;
    db_version: string;
    future_capacity: number;
    online_switch_type: 'user_confirm';
    resource_spec: {
      backend_group: {
        affinity: AffinityType;
        count: number; // 机器组数
        spec_id: number;
      };
      proxy: {
        affinity: AffinityType;
        count: number;
        spec_id: number;
      };
    };
    src_cluster: number;
    target_cluster_type: string;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    bkCloudId: 0,
    clusterId: 0,
    clusterType: '',
    clusterTypeName: '',
    currentSepc: '',
    currentShardNum: 0,
    currentSpecId: 0,
    dbVersion: '',
    disasterToleranceLevel: '',
    groupNum: 0,
    isLoading: false,
    proxy: {
      count: 0,
      id: 0,
    },
    rowKey: random(),
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
    srcCluster: '',
    srcClusterType: '',
    switchMode: '',
  });

  interface Props {
    data: IDataRow;
    inputedClusters?: string[];
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }
</script>
<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const deployPlanRef = ref<InstanceType<typeof RenderDeployPlan>>();
  const targetClusterTypeRef = ref<InstanceType<typeof RenderTargetClusterType>>();
  const versionRef = ref<InstanceType<typeof RenderTargetClusterVersion>>();
  const selectClusterType = ref('');

  watch(
    () => props.data.clusterType,
    (clusterType) => {
      selectClusterType.value = clusterType;
    },
    {
      immediate: true,
    },
  );

  const handleClusterTypeChange = (value: string) => {
    selectClusterType.value = value;
  };

  const handleInputFinish = (value: RedisModel) => {
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

  const getRowData = () => [
    targetClusterTypeRef.value!.getValue(),
    versionRef.value!.getValue(),
    deployPlanRef.value!.getValue(),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [targetClusterType, version] = rowData.map((item) =>
        item.status === 'fulfilled' ? item.value : item.reason,
      );
      emits('clone', {
        ...props.data,
        dbVersion: version,
        isLoading: false,
        rowKey: random(),
        targetClusterType,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue(true);
      return await Promise.all([
        targetClusterTypeRef.value!.getValue(),
        versionRef.value!.getValue(),
        deployPlanRef.value!.getValue(),
      ]).then((data: [string, string, ExposeValue]) => {
        const [targetClusterType, version, deployData] = data;
        return {
          capacity: deployData.capacity,
          cluster_shard_num: deployData.target_shard_num,
          current_cluster_type: props.data.clusterType,
          current_shard_num: props.data.currentShardNum,
          current_spec_id: props.data.currentSpecId,
          db_version: version,
          future_capacity: deployData.future_capacity,
          online_switch_type: 'user_confirm',
          resource_spec: {
            backend_group: {
              affinity: props.data.disasterToleranceLevel || AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
              count: deployData.count, // 机器组数
              spec_id: deployData.spec_id,
            },
            proxy: {
              affinity: AffinityType.CROS_SUBZONE,
              count: props.data.proxy.count,
              spec_id: props.data.proxy.id,
            },
          },
          src_cluster: props.data.clusterId,
          target_cluster_type: targetClusterType,
        };
      });
    },
  });
</script>
