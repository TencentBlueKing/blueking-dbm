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
    <!-- 跨行合并 -->
    <td
      v-if="data.cluster?.isGeneral || data.cluster?.isStart"
      :rowspan="data.cluster?.rowSpan"
      style="padding: 0;">
      <RenderText
        :data="data.cluster.domain"
        :is-loading="data.isLoading"
        :placeholder="$t('选择主机后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderSpec
        :data="data.spec"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.slaveNum"
        :is-loading="data.isLoading"
        :placeholder="$t('选择主机后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.targetNum"
        :is-loading="data.isLoading"
        :placeholder="$t('选择主机后自动生成')" />
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
  import RenderText from '@components/db-table-columns/RenderText.vue';

  import type { SpecInfo } from '@views/redis/common/spec-panel/Index.vue';

  import { random } from '@utils';

  import RenderHost from './RenderHost.vue';
  import RenderSpec from './RenderSpec.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string;
    clusterId: number;
    cluster: {
      domain: string;
      isStart: boolean;
      isGeneral: boolean;
      rowSpan: number;
    },
    targetNum: string;
    slaveNum?: number;
    spec?: SpecInfo
  }

  // 创建表格数据
  export const createRowData = (data?: IDataRow) => ({
    rowKey: random(),
    isLoading: false,
    ip: data?.ip ?? '',
    clusterId: 0,
    cluster: {
      domain: data?.cluster?.domain ?? '',
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
    targetNum: '',
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
