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
        <RenderCluster
          ref="clusterRef"
          :model-value="data.clusterData"
          @id-change="handleClusterIdChange"
          @input-create="handleCreate" />
      </td>
      <td style="padding: 0;">
        <RenderMasterSlave
          ref="hostRef"
          :cloud-id="cloudId"
          :disabled="!localClusterId"
          :domain="data.clusterData?.domain"
          :master-host="data.masterHostData"
          :slave-host="data.slaveHostData" />
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
  </tbody>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IHostData {
    bk_biz_id: number,
    bk_host_id: number,
    ip: string,
    bk_cloud_id: number,
  }
  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number,
      domain: string,
      cloudId: number | null
    },
    masterHostData?: IHostData,
    slaveHostData?: IHostData,
    backup_source: string,
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    masterHostData: data.masterHostData,
    slaveHostData: data.slaveHostData,
    backup_source: 'local',
  });
</script>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';

  import RenderCluster from '@views/mysql/common/edit-field/ClusterWithRelateCluster.vue';

  import RenderMasterSlave from './RenderMasterSlaveHost.vue';

  interface Props {
    data: IDataRow,
    removeable: boolean,
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

  const clusterRef = ref();
  const hostRef = ref();

  const localClusterId = ref(0);
  const cloudId = ref<number | null>(null);

  watch(() => props.data, () => {
    if (props.data.clusterData) {
      localClusterId.value = props.data.clusterData.id;
      cloudId.value = props.data.clusterData.cloudId;
    }
  }, {
    immediate: true,
  });
  const handleClusterIdChange = (idData: { id: number, cloudId: number | null }) => {
    localClusterId.value = idData.id;
    cloudId.value = idData.cloudId;
  };

  const handleCreate = (list: Array<string>) => {
    emits('add', list.map(domain => createRowData({
      clusterData: {
        id: 0,
        domain,
        cloudId: null,
      },
    })));
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
      return Promise.all([
        clusterRef.value.getValue(),
        hostRef.value.getValue(),
      ]).then(([clusterData, hostData]) => ({
        ...clusterData,
        ...hostData,
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
