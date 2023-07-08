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
    <td style="padding: 0;">
      <RenderHost
        :model-value="data.ip"
        @on-input-finish="handleInputFinish" />
    </td>
    <td
      style="padding: 0;">
      <RenderCluster
        :data="data.cluster"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0;">
      <RenderMasterInstance
        :data="data.masters"
        :is-loading="data.isLoading" />
    </td>

    <td style="padding: 0;">
      <RenderSlaveHost
        :data="data.slave"
        :is-loading="data.isLoading" />
    </td>
    <td>
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
</template>
<script lang="ts">
  import { random } from '@utils';

  import RenderCluster from './RenderCluster.vue';
  import RenderHost from './RenderHost.vue';
  import RenderMasterInstance from './RenderMasterInstance.vue';
  import RenderSlaveHost from './RenderSlaveHost.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string,
    clusterId: number;
    slave: string;
    cluster?: string;
    masters?:string[];
  }

  // 创建表格数据
  export const createRowData = (data?: IDataRow): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ip: data?.ip ?? '',
    clusterId: 0,
    cluster: data?.cluster ?? '',
    masters: data?.masters ?? [],
    slave: data?.slave ?? '',
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'onIpInputFinish', value: string): void
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

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
