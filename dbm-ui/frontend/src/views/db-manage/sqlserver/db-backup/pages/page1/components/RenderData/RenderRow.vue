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
        v-model="localClusterData" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderDbName
        ref="backupDbsRef"
        v-model="localDbList"
        check-not-exist
        :cluster-id="localClusterData?.id"
        required />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        v-model="localIgnoreDbList"
        :allow-asterisk="false"
        :required="false" />
    </td>
    <td style="padding: 0">
      <RenderFianlDb
        ref="fianlDbRef"
        :cluster-data="localClusterData"
        :db-list="localDbList"
        :ignore-db-list="localIgnoreDbList" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderDbName from '@views/db-manage/sqlserver/common/DbName.vue';

  import { random } from '@utils';

  import RenderCluster from './RenderCluster.vue';
  import RenderFianlDb from './RenderFianlDb.vue';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number;
      majorVersion: string;
    };
    dbList: string[];
    ignoreDbList: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    dbList: data.dbList || [],
    ignoreDbList: data.ignoreDbList || [],
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }
</script>
<script setup lang="ts">
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const backupDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const fianlDbRef = ref<InstanceType<typeof RenderFianlDb>>();

  const localClusterData = ref<Props['data']['clusterData']>();
  const localDbList = ref<Props['data']['dbList']>([]);
  const localIgnoreDbList = ref<Props['data']['ignoreDbList']>([]);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      if (props.data.dbList) {
        localDbList.value = props.data.dbList;
      }
      if (props.data.ignoreDbList) {
        localIgnoreDbList.value = props.data.ignoreDbList;
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

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value!.getValue(),
        backupDbsRef.value!.getValue('db_list'),
        ignoreDbsRef.value!.getValue('ignore_db_list'),
        fianlDbRef.value!.getValue(),
      ]).then(([clusterData, databasesData, ignoreDatabasesData, fianlDbData]) => ({
        ...clusterData,
        ...databasesData,
        ...ignoreDatabasesData,
        ...fianlDbData,
      }));
    },
  });
</script>
