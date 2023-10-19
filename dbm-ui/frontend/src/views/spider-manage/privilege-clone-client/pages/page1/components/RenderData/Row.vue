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
        <RenderSource
          ref="sourceRef"
          v-model="localSource" />
      </td>
      <td style="padding: 0;">
        <RenderModule
          ref="moduleRef"
          :model-value="data.module"
          :source="localSource" />
      </td>
      <td style="padding: 0;">
        <RenderCloudArea :source="localSource" />
      </td>
      <td style="padding: 0;">
        <RenderTarget
          ref="targetRef"
          :model-value="data.target"
          :source="localSource" />
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
  </tbody>
</template>
<script lang="ts">
  import { random } from '@utils';

  import RenderCloudArea from './RenderCloudArea.vue';
  import RenderModule from './RenderModule.vue';
  import RenderSource from './RenderSource.vue';
  import RenderTarget from './RenderTarget.vue';

  export interface IDataRow {
    rowKey: string;
    source?: {
      bk_cloud_id: number,
      bk_host_id: number,
      ip: string,
    },
    module?: string,
    target: string[]
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
    data: IDataRow,
    removeable: boolean,
    isFixed?: boolean,
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
  }

  interface Exposes{
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sourceRef = ref();
  const moduleRef = ref();
  const targetRef = ref();

  const localSource = ref<IDataRow['source']>();

  watch(() => props.data, () => {
    if (props.data) {
      localSource.value = props.data.source;
    }
  }, {
    immediate: true,
  });

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
      return Promise.all([
        sourceRef.value.getValue('master_ip'),
        moduleRef.value.getValue(),
        targetRef.value.getValue(),
      ]).then(([sourceData, moduleData, targetData]) => ({
        ...sourceData,
        ...moduleData,
        ...targetData,
      }));
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
