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
      <RenderSource
        ref="sourceRef"
        v-model="localSource" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderModule
        ref="moduleRef"
        :model-value="data.module"
        :source="localSource" />
    </td>
    <td style="padding: 0">
      <RenderTarget
        ref="targetRef"
        :model-value="data.target"
        :source="localSource" />
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
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  import RenderModule from './RenderModule.vue';
  import RenderSource from './RenderSource.vue';
  import RenderTarget from './RenderTarget.vue';

  export interface IDataRow {
    rowKey: string;
    source?: {
      bk_cloud_id: number;
      ip: string;
    };
    module?: string;
    target: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    source: data.source,
    module: data.module,
    target: data.target || [],
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
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sourceRef = ref<InstanceType<typeof RenderSource>>();
  const moduleRef = ref<InstanceType<typeof RenderModule>>();
  const targetRef = ref<InstanceType<typeof RenderTarget>>();
  const localSource = ref<IDataRow['source']>();

  watch(
    () => props.data,
    () => {
      if (props.data) {
        localSource.value = props.data.source;
      }
    },
    {
      immediate: true,
    },
  );

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
    Promise.allSettled([sourceRef.value!.getValue(), moduleRef.value!.getValue(), targetRef.value!.getValue()]).then(
      (rowData) => {
        const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
        emits(
          'clone',
          createRowData({
            rowKey: random(),
            source: props.data.source,
            target: rowInfo[2].target.split(','),
          }),
        );
      },
    );
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([sourceRef.value!.getValue(), moduleRef.value!.getValue(), targetRef.value!.getValue()]).then(
        ([sourceData, moduleData, targetData]) => ({
          ...sourceData,
          ...moduleData,
          ...targetData,
        }),
      );
    },
  });
</script>
