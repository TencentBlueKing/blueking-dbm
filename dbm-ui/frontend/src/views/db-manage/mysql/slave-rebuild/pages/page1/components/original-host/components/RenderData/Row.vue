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
      <RenderSlave
        ref="slaveRef"
        v-model="localSlave"
        :tab-list-config="tabListConfig" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderCluster
        ref="clusterRef"
        :slave="localSlave" />
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
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderSlave from '@views/db-manage/mysql/common/edit-field/InstanceWithSelector.vue';

  import { random } from '@utils';

  import RenderCluster from './RenderCluster.vue';

  export interface IDataRow {
    rowKey: string;
    slave?: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      instance_address: string;
      cluster_id: number;
    };
    clusterId?: number;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    slave: data.slave,
    clusterId: data.clusterId,
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

  const slaveRef = ref<InstanceType<typeof RenderSlave>>();
  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const localSlave = ref<IDataRow['slave']>();

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        name: t('目标从库实例'),
        tableConfig: {
          firsrColumn: {
            label: 'slave',
            role: 'slave',
          },
          multiple: false,
        },
      },
    ],
  } as any;

  watch(
    () => props.data,
    () => {
      if (props.data) {
        localSlave.value = props.data.slave;
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

  const getRowData = () => [slaveRef.value!.getValue(), clusterRef.value!.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [sourceData, clusterData] = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          slave: sourceData
            ? {
                bk_cloud_id: sourceData.slave.bk_cloud_id,
                bk_host_id: sourceData.slave.bk_host_id,
                ip: sourceData.slave.ip,
                port: sourceData.slave.port,
                instance_address: sourceData.slave.instance_address,
                cluster_id: clusterData.cluster_id,
              }
            : undefined,
          clusterId: clusterData.cluster_id,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([slaveRef.value!.getValue(), clusterRef.value!.getValue()]).then(
        ([sourceData, moduleData]) => ({
          slave: {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: sourceData.bk_cloud_id,
            ip: sourceData.ip,
            bk_host_id: sourceData.bk_host_id,
            port: sourceData.port,
            instance_address: sourceData.instance_address,
          },
          ...moduleData,
        }),
      );
    },
  });
</script>
