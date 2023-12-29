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
  <tbody>
    <tr>
      <td style="padding: 0;">
        <CellName
          ref="nameRef"
          :data="localRowData"
          :model-value="localRowData.name"
          @edit-change="handleNameChange" />
      </td>
      <td style="padding: 0;">
        <CellDesc
          ref="descRef"
          v-model="localRowData.desc" />
      </td>
      <td style="padding: 0;">
        <CellType />
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
              disabled: data.builtin
            }"
            @click="handleRemove">
            <DbIcon type="minus-fill" />
          </div>
        </div>
      </td>
    </tr>
  </tbody>
</template>
<script lang="ts">
  import { random } from '@utils';

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    name: data.name || '',
    desc: data.desc || '',
    builtin: false,
  });
</script>
<script setup lang="ts">
  import { renderTablekey } from '@components/render-table/Index.vue';

  import type { IVariable } from '../Index.vue';

  import CellDesc from './CellDesc.vue';
  import CellName from './CellName.vue';
  import CellType from './CellType.vue';

  export type IDataRow = IVariable

  interface Props {
    data: IDataRow,
  }

  interface Emits {
    (e: 'edit-change'): void,
    (e: 'add', params: IDataRow): void,
    (e: 'remove', data: IDataRow): void,
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { isOverflow: isFixed } = inject(renderTablekey)!;

  const nameRef = ref<InstanceType<typeof CellName>>();
  const descRef = ref<InstanceType<typeof CellDesc>>();

  const localRowData = reactive(createRowData());

  watch(() => props.data, () => {
    Object.assign(localRowData, props.data);
  }, {
    immediate: true,
  });

  const handleNameChange = () => {
    emits('edit-change');
  };

  const handleAppend = () => {
    emits('add', createRowData());
  };

  const handleRemove = () => {
    if (props.data.builtin) {
      return;
    }
    emits('remove', props.data);
  };
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
        color: #dcdee5 !important;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 18px;
      }
    }
  }
</style>
