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
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.role"
        :is-loading="data.isLoading"
        :placeholder="$t('输入主机后自动生成')" />
    </td>
    <!-- 跨行合并 -->
    <td
      v-if="data.cluster.isGeneral || data.cluster.isStart"
      :rowspan="data.cluster.rowSpan"
      style="padding: 0">
      <RenderText
        :data="data.cluster.domain"
        :is-loading="data.isLoading"
        :placeholder="$t('选择主机后自动生成')" />
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
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderHost from '@views/redis/common/edit-field/HostName.vue';
  import type { SpecInfo } from '@views/redis/common/spec-panel/Index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string;
    role: string;
    clusterId: number;
    bkCloudId: number;
    cluster: {
      domain: string;
      isStart: boolean;
      isGeneral: boolean;
      rowSpan: number;
    };
    spec?: SpecInfo;
  }

  // 创建表格数据
  export const createRowData = (data?: IDataRow): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ip: data?.ip ?? '',
    role: data?.role ?? '',
    clusterId: 0,
    bkCloudId: 0,
    cluster: {
      domain: data?.cluster?.domain ?? '',
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputedIps?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'onIpInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedIps: () => [],
  });

  const emits = defineEmits<Emits>();

  const hostRef = ref();

  const handleInputFinish = (value: string) => {
    emits('onIpInputFinish', value);
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
      return hostRef.value.getValue();
    },
  });
</script>
