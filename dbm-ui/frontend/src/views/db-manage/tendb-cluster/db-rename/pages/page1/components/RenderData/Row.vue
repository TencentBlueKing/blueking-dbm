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
    <td style="padding: 0">
      <RenderCluster
        ref="clusterRef"
        :model-value="data.clusterData"
        @id-change="handleClusterIdChange"
        @input-create="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="fromDatabaseRef"
        check-exist
        :cluster-id="localClusterId"
        :model-value="data.fromDatabase"
        :placeholder="t('请输入单个源 DB 名')"
        single />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="toDatabaseRef"
        check-not-exist
        :cluster-id="localClusterId"
        :model-value="data.toDatabase"
        :placeholder="t('请输入单个新 DB 名')"
        single />
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
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
    };
    fromDatabase?: string;
    toDatabase?: string;
  }

  export type IDataRowBatchKey = keyof Omit<IDataRow, 'rowKey' | 'clusterData'>;

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    fromDatabase: data.fromDatabase,
    toDatabase: data.toDatabase,
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderCluster from './RenderCluster.vue';
  import RenderDbName from './RenderDbName.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: IDataRow): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
    (e: 'clone', value: IDataRow): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref();
  const fromDatabaseRef = ref();
  const toDatabaseRef = ref();
  const localClusterId = ref(0);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClusterIdChange = (clusterId: number) => {
    localClusterId.value = clusterId;
  };

  const handleInputFinish = (domain: string) => {
    emits('clusterInputFinish', domain);
  };

  const handleAppend = () => {
    emits('add', createRowData());
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  const getRowData = () => [
    clusterRef.value.getValue(),
    fromDatabaseRef.value.getValue('from_database'),
    toDatabaseRef.value.getValue('to_database'),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [clusterData, fromDatabaseData, toDatabaseData] = rowData.map((item) =>
        item.status === 'fulfilled' ? item.value : item.reason,
      );
      emits(
        'clone',
        createRowData({
          clusterData: {
            id: clusterData.cluster_id,
            domain: '',
          },
          fromDatabase: fromDatabaseData.from_database,
          toDatabase: toDatabaseData.to_database,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(([clusterData, fromDatabaseData, toDatabaseData]) => ({
        ...clusterData,
        ...fromDatabaseData,
        ...toDatabaseData,
      }));
    },
  });
</script>
