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
      <td style="padding: 0">
        <RenderOriginalProxy
          ref="originRef"
          :model-value="data.originProxyIp"
          @input-create="handleCreate"
          @input-finish="handleOriginProxyInputFinish" />
      </td>
      <td style="padding: 0">
        <RenderTargetProxyIp
          ref="targetRef"
          :cloud-id="data.originProxyIp?.bk_cloud_id ?? null"
          :disabled="!data.originProxyIp?.instance_address"
          :model-value="data.targetProxyIp"
          :target-ip="data.originProxyIp?.ip" />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @clone="handleClone"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface IProxyData {
    cluster_id: number;
    bk_host_id: number;
    bk_cloud_id: number | null;
    port: number;
    ip: string;
    instance_address: string;
  }

  export interface IHostData {
    bk_host_id: number;
    bk_cloud_id: number;
    ip: string;
  }

  export interface IDataRow {
    rowKey: string;
    originProxyIp?: IProxyData;
    targetProxyIp?: IHostData;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    originProxyIp: data.originProxyIp ?? ({} as IDataRow['originProxyIp']),
    targetProxyIp: data.targetProxyIp ?? ({} as IDataRow['targetProxyIp']),
  });
</script>
<script setup lang="ts">
  import { ref } from 'vue';

  import RenderOriginalProxy from './RenderOriginalProxy.vue';
  import RenderTargetProxyIp from './RenderTargetProxyIp.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'originProxyInputFinish', value: IProxyData): void;
    (e: 'clone', value: IDataRow): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const targetRef = ref();
  const originRef = ref();

  const handleOriginProxyInputFinish = (value: IProxyData) => {
    emits('originProxyInputFinish', value);
  };

  const handleCreate = (list: Array<string>) => {
    emits(
      'add',
      list.map((instanceAddress) =>
        createRowData({
          originProxyIp: {
            cluster_id: 0,
            bk_host_id: 0,
            bk_cloud_id: null,
            port: 0,
            ip: '',
            instance_address: instanceAddress,
          },
        }),
      ),
    );
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

  const getRowData = () => [originRef.value.getValue(), targetRef.value.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          originProxyIp: props.data.originProxyIp,
          targetProxyIp: rowInfo[1].target_proxy,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(([originData, targetData]) => ({
        ...originData,
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
