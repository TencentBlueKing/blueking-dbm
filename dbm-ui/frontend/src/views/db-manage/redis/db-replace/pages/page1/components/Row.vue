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
      <RenderHost
        ref="hostRef"
        :data="data.ip"
        :inputed="inputedIps"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderRole
        :data="data.role"
        :is-loading="data.isLoading" />
    </td>
    <!-- 跨行合并 -->
    <td
      v-if="data.cluster.isGeneral || data.cluster.isStart"
      :rowspan="data.cluster.rowSpan"
      style="padding: 0">
      <RenderCluster
        :data="data.cluster.domain"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderSpec
        :data="data.spec"
        :hide-qps="data.role === 'proxy'"
        is-ignore-counts
        :is-loading="data.isLoading" />
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
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import RenderHost from '@views/db-manage/redis/common/edit-field/HostName.vue';
  import RenderCluster from '@views/db-manage/redis/common/edit-field/RenderCluster.vue';
  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  import { random } from '@utils';

  import RenderRole from './RenderRole.vue';

  export interface IDataRow {
    bkCloudId: number;
    cluster: {
      domain: string;
      isGeneral: boolean;
      isStart: boolean;
      rowSpan: number;
    };
    clusterIds: number[];
    ip: string;
    isLoading: boolean;
    role: string;
    rowKey: string;
    spec?: SpecInfo;
  }

  // 创建表格数据
  export const createRowData = (data?: IDataRow): IDataRow => ({
    bkCloudId: 0,
    cluster: {
      domain: data?.cluster?.domain ?? '',
      isGeneral: true,
      isStart: false,
      rowSpan: 1,
    },
    clusterIds: [],
    ip: data?.ip ?? '',
    isLoading: false,
    role: data?.role ?? '',
    rowKey: random(),
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    inputedIps?: string[];
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'onIpInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedIps: () => [],
  });

  const emits = defineEmits<Emits>();

  const hostRef = ref<InstanceType<typeof RenderHost>>();

  const handleInputFinish = (value: string) => {
    emits('onIpInputFinish', value.split(':')[1]);
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
    Promise.allSettled([hostRef.value.getValue()]).then((rowData) => {
      emits('clone', {
        ...props.data,
        isLoading: false,
        rowKey: random(),
      });
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return hostRef.value!.getValue(true);
    },
  });
</script>
