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
      <RenderInstance
        ref="instanceRef"
        :data="data.clusterData?.instance"
        @input-finish="handleClusterIdChange" />
    </FixedColumn>
    <!-- 跨行合并 -->
    <td
      v-if="data.spanData.isGeneral || data.spanData.isStart"
      :rowspan="data.spanData.rowSpan"
      style="padding: 0">
      <RenderText
        :data="data.clusterData?.domain"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterData?.specName"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderCurrentVersion
        ref="currentVersionRef"
        :data="data.clusterData" />
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
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderInstance from '@views/db-manage/redis/common/edit-field/RenderInstance.vue';

  import { random } from '@utils';

  import RenderCurrentVersion from './RenderCurrentVersion.vue';

  export interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    spanData: {
      isStart: boolean;
      isGeneral: boolean;
      rowSpan: number;
    };
    clusterData?: {
      instance: string;
      domain: string;
      clusterId: number;
      clusterType: string;
      specId: number;
      specName: string;
    };
    master?: IHostData;
    slave?: IHostData;
  }

  // 创建表格数据
  export const createRowData = (clusterData?: NonNullable<IDataRow['clusterData']>): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    spanData: {
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
    clusterData,
  });
</script>

<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: IDataRow[]): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_id: number;
      resource_spec: {
        backend_group: {
          spec_id: number;
          count: number;
        };
      };
      old_nodes: {
        master: IHostData[];
        slave: IHostData[];
      };
      display_info: {
        instance: Awaited<ReturnType<ComponentExposed<typeof RenderInstance>['getValue']>>;
        db_version: string[];
      };
    }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const instanceRef = ref<InstanceType<typeof RenderInstance>>();
  const currentVersionRef = ref<InstanceType<typeof RenderCurrentVersion>>();

  const handleClusterIdChange = (value: string) => {
    emits('inputFinish', value);
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

  const handleClone = () => {
    Promise.allSettled([instanceRef.value!.getValue(true)]).then(() => {
      emits('clone', createRowData(props.data.clusterData));
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all([instanceRef.value!.getValue(true), currentVersionRef.value!.getValue()]).then(
        ([instanceData, versionData]) => {
          const clusterInfo = props.data.clusterData!;
          return {
            cluster_id: clusterInfo.clusterId,
            resource_spec: {
              backend_group: {
                spec_id: clusterInfo.specId,
                count: 1,
              },
            },
            old_nodes: {
              master: [props.data.master!],
              slave: [props.data.slave!],
            },
            display_info: {
              instance: instanceData,
              db_version: versionData,
            },
          };
        },
      );
    },
  });
</script>
