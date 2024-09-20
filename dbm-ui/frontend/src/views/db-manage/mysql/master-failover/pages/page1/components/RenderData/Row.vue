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
      <RenderMaster
        ref="masterHostRef"
        :model-value="data.masterData"
        :tab-list-config="tabListConfig"
        type="ip"
        @instance-change="handleMasterDataChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderSlave
        ref="slaveHostRef"
        :cluster-list="relatedClusterList"
        :model-value="data.slaveData" />
    </td>
    <td style="padding: 0">
      <RenderCluster
        ref="clusterRef"
        :master-data="localMasterData"
        @change="handleClusterChange" />
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
  import { ref, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderMaster from '@views/db-manage/mysql/common/edit-field/InstanceWithSelector.vue';

  import { random } from '@utils';

  import RenderCluster from './RenderCluster.vue';
  import RenderSlave from './RenderSlave.vue';

  export type IHostData = {
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  };

  export interface IDataRow {
    rowKey: string;
    masterData?: IHostData;
    slaveData?: IHostData;
    clusterData?: {
      id: number;
      domain: string;
    };
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    masterData: data.masterData,
    slaveData: data.slaveData,
    clusterData: data.clusterData,
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

  const { t } = useI18n();

  const masterHostRef = ref();
  const slaveHostRef = ref();
  const clusterRef = ref();

  const localMasterData = shallowRef();

  const relatedClusterList = shallowRef<number[]>([]);

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        name: t('故障主库主机'),
        tableConfig: {
          multiple: false,
        },
      },
    ],
  } as any;

  watch(
    () => props.data,
    () => {
      localMasterData.value = props.data.masterData;
    },
    {
      immediate: true,
    },
  );

  const handleMasterDataChange = (data: IHostData) => {
    localMasterData.value = data;
  };

  const handleClusterChange = (data: number[]) => {
    relatedClusterList.value = data;
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

  const getRowData = () => [masterHostRef.value.getValue(), slaveHostRef.value.getValue(), clusterRef.value.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          masterData: props.data.masterData,
          slaveData: rowInfo[1].slave_ip,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        masterHostRef.value.getValue(),
        slaveHostRef.value.getValue(),
        clusterRef.value.getValue(),
      ]).then(([masterHostData, slaveHostData, clusterData]) => ({
        master_ip: {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_host_id: masterHostData.bk_host_id,
          ip: masterHostData.ip,
          bk_cloud_id: masterHostData.bk_cloud_id,
        },
        ...slaveHostData,
        ...clusterData,
      }));
    },
  });
</script>
