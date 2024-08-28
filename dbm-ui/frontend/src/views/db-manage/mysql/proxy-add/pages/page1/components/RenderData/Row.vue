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
      <RenderCluster
        ref="clusterRef"
        :model-value="data.clusterData"
        :relate-cluster-tips="t('同主机关联的其他集群，勾选后一并添加')"
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderProxy
        ref="proxyRef"
        :cloud-id="cloudId"
        :disabled="!localClusterId"
        :domain="data.clusterData?.domain"
        :model-value="data.proxyIp" />
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
  import { random } from '@utils';

  export interface IHostData {
    bk_host_id: number;
    bk_cloud_id: number;
    ip: string;
  }

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number | null;
    };
    proxyIp?: IHostData;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    proxyIp: data.proxyIp,
  });
</script>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderCluster from '@views/db-manage/mysql/common/edit-field/ClusterWithRelateCluster.vue';

  import RenderProxy from './RenderProxy.vue';

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

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const proxyRef = ref<InstanceType<typeof RenderProxy>>();
  const localClusterId = ref(0);
  const cloudId = ref<number | null>(null);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
        cloudId.value = props.data.clusterData.cloudId;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClusterIdChange = (idData: { id: number; cloudId: number | null }) => {
    localClusterId.value = idData.id;
    cloudId.value = idData.cloudId;
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

  const getRowData = () => [clusterRef.value.getValue(), proxyRef.value.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          clusterData: props.data.clusterData,
          proxyIp: rowInfo[1].new_proxy,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([clusterRef.value!.getValue(), proxyRef.value!.getValue()]).then(
        ([clusterData, proxyData]) => ({
          ...clusterData,
          ...proxyData,
        }),
      );
    },
  });
</script>
