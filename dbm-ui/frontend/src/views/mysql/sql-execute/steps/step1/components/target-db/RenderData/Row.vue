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
      <RenderDbName
        ref="dbnamesRef"
        :model-value="data.dbnames"
        @change="handleDbnamesChange" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbnamesRef"
        :model-value="data.ignore_dbnames"
        :required="false"
        @change="handleIgnoreDbnamesChange" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    dbnames: string[];
    ignore_dbnames: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    dbnames: data.dbnames || [],
    ignore_dbnames: data.ignore_dbnames || [],
  });
</script>
<script setup lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderDbName from './RenderDbName.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: IDataRow): void;
    (e: 'remove'): void;
    (e: 'change', value: IDataRow): void;
  }

  interface Exposes {
    getValue: () => Promise<IDataRow>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const dbnamesRef = ref();
  const ignoreDbnamesRef = ref();
  const dbnames = ref(props.data.dbnames);
  const ignoreDbnames = ref(props.data.ignore_dbnames);

  const triggerChange = () => {
    emits('change', {
      rowKey: props.data.rowKey,
      dbnames: dbnames.value,
      ignore_dbnames: ignoreDbnames.value,
    });
  };

  const handleDbnamesChange = (value: string[]) => {
    dbnames.value = value;
    triggerChange();
  };
  const handleIgnoreDbnamesChange = (value: string[]) => {
    ignoreDbnames.value = value;
    triggerChange();
  };

  const handleAppend = () => {
    emits('add', createRowData());
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([dbnamesRef.value.getValue(), ignoreDbnamesRef.value.getValue()]).then(() => ({
        rowKey: props.data.rowKey,
        dbnames: dbnames.value,
        ignore_dbnames: ignoreDbnames.value,
      }));
    },
  });
</script>
