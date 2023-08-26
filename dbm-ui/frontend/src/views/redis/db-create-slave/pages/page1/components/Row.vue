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
        ref="hostRef"
        :data="data.ip"
        :inputed="inputedIps"
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
      <RenderSlaveHost
        :data="data.slaveHost"
        :is-loading="data.isLoading" />
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
</template>
<script lang="ts">
  import RenderText from '@components/tools-table-common/RenderText.vue';
  import RenderSpec from '@components/tools-table-spec/index.vue';

  import RenderHost from '@views/redis/common/edit-field/HostName.vue';
  import type { SpecInfo } from '@views/redis/common/spec-panel/Index.vue';

  import { random } from '@utils';

  import RenderSlaveHost from './RenderSlaveHost.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string;
    clusterId: number;
    bkCloudId: number;
    bkHostId: number;
    cluster: {
      domain: string;
      isStart: boolean;
      isGeneral: boolean;
      rowSpan: number;
    },
    targetNum: number;
    slaveNum?: number;
    spec?: SpecInfo;
    slaveHost?: {
      faults: number;
      total: number;
    }
  }

  // 创建表格数据
  export const createRowData = (data?: IDataRow) => ({
    rowKey: random(),
    isLoading: false,
    ip: data?.ip ?? '',
    clusterId: 0,
    bkCloudId: 0,
    bkHostId: 0,
    cluster: {
      domain: data?.cluster?.domain ?? '',
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
    targetNum: 1,
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    inputedIps?: string[],
    isFixed?: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'onIpInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedIps: () => ([]),
    isFixed: false,
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
