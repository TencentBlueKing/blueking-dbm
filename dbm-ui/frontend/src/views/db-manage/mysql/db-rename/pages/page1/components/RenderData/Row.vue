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
        :cluster-types="clusterTypes"
        :model-value="data.clusterData"
        only-one-type
        @id-change="handleClusterIdChange" />
    </FixedColumn>
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
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      type: string;
    };
    fromDatabase?: string;
    toDatabase?: string;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    fromDatabase: data.fromDatabase,
    toDatabase: data.toDatabase,
  });

  export type IDataRowBatchKey = keyof Omit<IDataRow, 'rowKey' | 'clusterData'>;
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderCluster from '@views/db-manage/mysql/common/edit-field/ClusterName.vue';

  import RenderDbName from './RenderDbName.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterTypes?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const fromDatabaseRef = ref<InstanceType<typeof RenderDbName>>();
  const toDatabaseRef = ref<InstanceType<typeof RenderDbName>>();
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
    emits('clusterInputFinish', clusterId);
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

  const handleClone = () => {
    Promise.allSettled([
      clusterRef.value!.getValue(true),
      fromDatabaseRef.value!.getValue('from_database'),
      toDatabaseRef.value!.getValue('to_database'),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          rowKey: random(),
          clusterData: props.data.clusterData,
          fromDatabase: rowInfo[1].from_database,
          toDatabase: rowInfo[2].to_database,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value!.getValue(),
        fromDatabaseRef.value!.getValue('from_database'),
        toDatabaseRef.value!.getValue('to_database'),
      ]).then(([clusterData, backupLocalData, dbPatternsData]) => ({
        ...clusterData,
        ...backupLocalData,
        ...dbPatternsData,
      }));
    },
  });
</script>
