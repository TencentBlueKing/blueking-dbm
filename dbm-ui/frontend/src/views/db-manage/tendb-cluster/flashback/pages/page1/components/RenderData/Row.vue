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
        @input-create="handleCreate" />
    </td>
    <td style="padding: 0">
      <RenderStartTime
        ref="startTimeRef"
        v-model="localStartTime" />
    </td>
    <td style="padding: 0">
      <RenderEndTime
        ref="endTimeRef"
        v-model="localEndTime"
        :start-time="localStartTime" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="databasesRef"
        v-model="localDatabases"
        :cluster-id="localClusterId"
        required />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="databasesIgnoreRef"
        v-model="localDatabaseIgnore"
        :allow-asterisk="false"
        :cluster-id="localClusterId"
        :rules="ingoredbAndTableNameBaseRules" />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablesRef"
        v-model="localTables"
        :cluster-id="localClusterId"
        required />
    </td>
    <td style="padding: 0">
      <RenderTableName
        ref="tablesIgnoreRef"
        v-model="localTablesIgnore"
        :allow-asterisk="false"
        :cluster-id="localClusterId"
        :rules="ingoredbAndTableNameBaseRules" />
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
    startTime?: string;
    endTime?: string;
    databases?: string[];
    tables?: string[];
    databasesIgnore?: string[];
    tablesIgnore?: string[];
  }

  export type IDataRowBatchKey = keyof Omit<IDataRow, 'rowKey' | 'clusterData'>;

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    startTime: data.startTime,
    endTime: data.endTime,
    databases: data.databases,
    tables: data.tables,
    databasesIgnore: data.databasesIgnore,
    tablesIgnore: data.tablesIgnore,
  });
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RenderDbName from '@views/db-manage/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/db-manage/mysql/common/edit-field/TableName.vue';

  import RenderCluster from './RenderCluster.vue';
  import RenderEndTime from './RenderEndTime.vue';
  import RenderStartTime from './RenderStartTime.vue';

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

  const clusterRef = ref();
  const startTimeRef = ref();
  const endTimeRef = ref();
  const databasesRef = ref();
  const tablesRef = ref();
  const databasesIgnoreRef = ref();
  const tablesIgnoreRef = ref();

  const localClusterId = ref(0);
  const localStartTime = ref<string>();
  const localEndTime = ref<string>();
  const localDatabases = ref<string[]>();
  const localTables = ref<string[]>();
  const localDatabaseIgnore = ref<string[]>();
  const localTablesIgnore = ref<string[]>();

  const ingoredbAndTableNameBaseRules = [
    {
      validator: (value: string[]) => {
        if (value.length < 1) {
          return true;
        }

        return _.every(value, (item) => !/\*/.test(item));
      },
      message: t('不支持 *'),
      trigger: 'change',
    },
    {
      validator: (value: string[]) => {
        if (_.some(value, (item) => /[*%?]/.test(item))) {
          return value.length < 2;
        }
        return true;
      },
      message: t('含通配符的单元格仅支持输入单个对象'),
      trigger: 'change',
    },
    {
      validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
      message: t('% 不允许单独使用'),
      trigger: 'change',
    },
  ];

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
        localStartTime.value = props.data.startTime;
        localEndTime.value = props.data.endTime;
        localDatabases.value = props.data.databases;
        localTables.value = props.data.tables;
        localDatabaseIgnore.value = props.data.databasesIgnore;
        localTablesIgnore.value = props.data.tablesIgnore;
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleClusterIdChange = (id: number) => {
    localClusterId.value = id;
  };

  const handleCreate = (list: Array<string>) => {
    emits(
      'add',
      list.map((domain) =>
        createRowData({
          clusterData: {
            id: 0,
            domain,
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

  const getRowData = () => [
    clusterRef.value.getValue(),
    startTimeRef.value.getValue(),
    endTimeRef.value.getValue(),
    databasesRef.value.getValue('databases'),
    tablesRef.value.getValue('tables'),
    databasesIgnoreRef.value.getValue('databases_ignore'),
    tablesIgnoreRef.value.getValue('tables_ignore'),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [
        clusterData,
        startTimeData,
        endTimeData,
        databasesData,
        tablesData,
        databasesIgnoreData,
        tablesIgnoreData,
      ] = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          clusterData: {
            id: clusterData.cluster_id,
            domain: '',
          },
          startTime: startTimeData.start_time,
          endTime: endTimeData.end_time,
          databases: databasesData.databases,
          tables: tablesData.tables,
          databasesIgnore: databasesIgnoreData.databases_ignore,
          tablesIgnore: tablesIgnoreData.tables_ignore,
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(
        ([
          clusterData,
          startTimeData,
          endTimeData,
          databasesData,
          tablesData,
          databasesIgnoreData,
          tablesIgnoreData,
        ]) => ({
          ...clusterData,
          ...startTimeData,
          ...endTimeData,
          ...databasesData,
          ...tablesData,
          ...databasesIgnoreData,
          ...tablesIgnoreData,
        }),
      );
    },
  });
</script>
