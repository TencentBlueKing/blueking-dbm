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
    <FixedColumn fixed="left">
      <RenderCluster
        ref="clusterRef"
        :model-value="clusterInfo"
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderCurrentVersion
        :charset="localCharset"
        :data="data.clusterData"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderTargetVersion
        ref="targetVersionRef"
        :data="data.clusterData"
        :is-loading="data.isLoading"
        :target-module="data.targetModule"
        :target-package="data.targetPackage"
        :target-version="data.targetVersion"
        @module-change="handleModuleChange" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  import RenderCurrentVersion from '../RenderCurrentVersion.vue';

  import RenderCluster from './RenderCluster.vue';
  import RenderTargetVersion from './RenderTargetVersion.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterData?: {
      domain: string;
      clusterId: number;
      clusterType: string;
      currentVersion: string;
      packageVersion: string;
      moduleName: string;
      moduleId: number;
    };
    targetVersion?: string;
    targetPackage?: number;
    targetModule?: number;
  }

  // 创建表格数据
  export const createRowData = (clusterData?: NonNullable<IDataRow['clusterData']>): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    clusterData,
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }
</script>

<script setup lang="ts">
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const targetVersionRef = ref<InstanceType<typeof RenderTargetVersion>>();
  const localCharset = ref('');

  const clusterInfo = computed(() => {
    if (props.data.clusterData) {
      return {
        id: props.data.clusterData.clusterId,
        domain: props.data.clusterData.domain,
      };
    }
    return undefined;
  });

  const handleClusterIdChange = (clusterId: number) => {
    emits('clusterInputFinish', clusterId);
  };

  const handleModuleChange = (value: string) => {
    localCharset.value = value;
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
      return await Promise.all([clusterRef.value!.getValue(true), targetVersionRef.value!.getValue()]).then((data) => {
        const [clusterData, targetVersionData] = data;
        const clusterInfo = props.data.clusterData!;
        Object.assign(targetVersionData.display_info, {
          cluster_type: clusterInfo.clusterType,
          current_version: clusterInfo.currentVersion,
          current_package: clusterInfo.packageVersion,
          charset: localCharset.value,
          current_module_name: clusterInfo.moduleName,
        });
        return {
          ...clusterData,
          ...targetVersionData,
        };
      });
    },
  });
</script>
