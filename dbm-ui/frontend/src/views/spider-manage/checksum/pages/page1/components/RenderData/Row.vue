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
  <tbody :key="data.rowKey">
    <template
      v-for="(backupInfoItem, index) in localBackupInfos"
      :key="index">
      <tr>
        <td
          v-if="index === 0"
          :rowspan="localBackupInfos.length"
          style="padding: 0">
          <RenderCluster
            ref="clusterRefs"
            :model-value="data.clusterData"
            @id-change="handleClusterIdChange" />
        </td>
        <td
          v-if="index === 0"
          :rowspan="localBackupInfos.length"
          style="padding: 0">
          <RenderScope
            ref="scopeRefs"
            :cluster-id="localClusterId"
            :model-value="data.scope"
            @change="handleScopeChange" />
        </td>
        <td
          v-if="index === 0"
          :rowspan="localBackupInfos.length"
          style="padding: 0">
          <RenderSlave
            ref="slaveRefs"
            :cluster-id="localClusterId"
            :model-value="backupInfoItem.slave"
            :scope="localScope"
            @change="handleSlaveChange" />
        </td>
        <td
          name="master"
          style="padding: 0">
          <RenderMaster
            ref="masterRefs"
            :cluster-id="localClusterId"
            :model-value="backupInfoItem.master"
            :scope="localScope"
            :slave="backupInfoItem.slave" />
        </td>
        <td style="padding: 0">
          <RenderDbName
            ref="dbPatternsRefs"
            :cluster-id="localClusterId"
            :model-value="backupInfoItem.dbPatterns" />
        </td>
        <td style="padding: 0">
          <RenderDbName
            ref="ignoreDbsRefs"
            v-model:model-value="backupInfoItem.ignoreDbs"
            :cluster-id="localClusterId"
            :required="false" />
        </td>
        <td style="padding: 0">
          <RenderTableName
            ref="tablePatternsRefs"
            :cluster-id="localClusterId"
            :model-value="backupInfoItem.tablePatterns" />
        </td>
        <td style="padding: 0">
          <RenderIgnoreTables
            ref="ignoreTablesRefs"
            :cluster-id="localClusterId"
            :ignore-dbs="backupInfoItem.ignoreDbs"
            :model-value="backupInfoItem.ignoreTables" />
        </td>
        <OperateColumn
          :removeable="removeable"
          :show-add="false"
          @remove="handleRemove" />
      </tr>
    </template>
  </tbody>
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
    scope: string;
    backupInfos: {
      slave: string;
      master: string;
      dbPatterns?: string[];
      ignoreDbs?: string[];
      tablePatterns?: string[];
      ignoreTables?: string[];
    }[];
  }

  const createBackupInfo = (data = {} as Partial<IDataRow['backupInfos'][0]>) => ({
    master: data.master || '',
    slave: data.slave || '',
    dbPatterns: data.dbPatterns,
    tablePatterns: data.tablePatterns,
    ignoreDbs: data.ignoreDbs,
    ignoreTables: data.ignoreTables,
  });

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => {
    const backupInfos = data.backupInfos ? data.backupInfos[0] : ({} as IDataRow['backupInfos'][0]);
    return {
      rowKey: random(),
      clusterData: data.clusterData,
      scope: data.scope || '',
      backupInfos: [createBackupInfo(backupInfos)],
    };
  };
</script>
<script setup lang="ts">
  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/mysql/common/edit-field/TableName.vue';

  import RenderCluster from './RenderCluster.vue';
  import RenderIgnoreTables from './RenderIgnoreTables.vue';
  import RenderMaster from './RenderMaster.vue';
  import RenderScope from './RenderScope.vue';
  import RenderSlave from './RenderSlave.vue';

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

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRefs = ref();
  const scopeRefs = ref();
  const slaveRefs = ref();
  const masterRefs = ref();
  const dbPatternsRefs = ref();
  const ignoreDbsRefs = ref();
  const tablePatternsRefs = ref();
  const ignoreTablesRefs = ref();

  const localClusterId = ref(0);
  const localBackupInfos = ref<IDataRow['backupInfos']>([]);
  const localScope = ref('');

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterId.value = props.data.clusterData.id;
      }
      if (props.data.scope) {
        localScope.value = props.data.scope;
      }
      if (props.data.backupInfos) {
        localBackupInfos.value = props.data.backupInfos;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClusterIdChange = (clusterId: number) => {
    localClusterId.value = clusterId;
  };

  const handleScopeChange = (scope: string) => {
    localScope.value = scope;
    localBackupInfos.value = [createBackupInfo()];
  };

  const handleSlaveChange = (slaveInstanceList: string[]) => {
    if (slaveInstanceList.length < 1) {
      localBackupInfos.value = [createBackupInfo()];
      return;
    }
    const localBackupInfosSlaveInstanceMap = localBackupInfos.value.reduce(
      (result, item) =>
        Object.assign({}, result, {
          [item.slave]: item,
        }),
      {} as Record<string, IDataRow['backupInfos'][0]>,
    );
    localBackupInfos.value = slaveInstanceList.reduce(
      (result, slaveInstanceItem) => {
        if (localBackupInfosSlaveInstanceMap[slaveInstanceItem]) {
          result.push(localBackupInfosSlaveInstanceMap[slaveInstanceItem]);
        } else {
          result.push(
            createBackupInfo({
              slave: slaveInstanceItem,
            }),
          );
        }

        return result;
      },
      [] as IDataRow['backupInfos'],
    );
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
        Promise.all(clusterRefs.value.map((item: any) => item.getValue())),
        Promise.all(scopeRefs.value.map((item: any) => item.getValue())),
        Promise.all(slaveRefs.value.map((item: any) => item.getValue())),
        Promise.all(masterRefs.value.map((item: any) => item.getValue())),
        Promise.all(dbPatternsRefs.value.map((item: any) => item.getValue('db_patterns'))),
        Promise.all(tablePatternsRefs.value.map((item: any) => item.getValue('table_patterns'))),
        Promise.all(ignoreDbsRefs.value.map((item: any) => item.getValue('ignore_dbs'))),
        Promise.all(ignoreTablesRefs.value.map((item: any) => item.getValue('ignore_tables'))),
      ]).then(
        ([
          clusterList,
          scopeList,
          slaveList,
          masterList,
          dbPatternsList,
          tablePatternsList,
          ignoreDbsList,
          ignoreTablesList,
        ]) => {
          const slaveListResult = slaveList[0] as string[];

          return {
            ...clusterList[0],
            ...scopeList[0],
            backup_infos: slaveListResult.reduce((result, item, index) => {
              result.push({
                slave: slaveListResult[index],
                ...masterList[index],
                ...dbPatternsList[index],
                ...tablePatternsList[index],
                ...ignoreDbsList[index],
                ...ignoreTablesList[index],
              });
              return result;
            }, [] as any[]),
          };
        },
      );
    },
  });
</script>
