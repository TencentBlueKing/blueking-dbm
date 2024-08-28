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
        :data="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderSpec
        ref="sepcRef"
        :cloud-id="data.cloudId"
        :cluster-type="data.clusterType"
        :data="data.specId" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="numRef"
        :data="data.targetNum"
        :is-loading="data.isLoading"
        :min="data.spec?.count" />
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
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderTargetCluster from '@views/db-manage/tendb-cluster/common/edit-field/ClusterName.vue';
  import type { SpecInfo } from '@views/db-manage/tendb-cluster/common/spec-panel-select/components/Panel.vue';
  import RenderSpec from '@views/db-manage/tendb-cluster/common/spec-panel-select/Index.vue';

  import { random } from '@utils';

  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    clusterType: string;
    cloudId: number;
    bizId: number;
    spec?: SpecInfo;
    specId?: number;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    resource_spec: {
      spider_slave_ip_list: {
        spec_id: 1;
        count: 2;
      } & SpecInfo;
    };
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    clusterType: '',
    cloudId: 0,
    bizId: 0,
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'onClusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const sepcRef = ref();
  const numRef = ref();

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

  const getRowData = () => [clusterRef.value.getValue(), sepcRef.value.getValue(), numRef.value.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits('clone', {
        ...props.data,
        rowKey: random(),
        isLoading: false,
        specId: rowInfo[1].spec_id,
        targetNum: rowInfo[2].count,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      return Promise.all(getRowData()).then((data) => ({
        cluster_id: props.data.clusterId,
        resource_spec: {
          spider_slave_ip_list: {
            ...props.data.spec,
            ...data[1],
            ...data[2],
          },
        },
      }));
    },
  });
</script>
