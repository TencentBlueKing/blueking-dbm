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
  <BatchInput
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    ref="table"
    class="mt-16 mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="item.cluster"
        allows-duplicates
        :selected="selected"
        @batch-edit="handleBatchEditCluster" />
      <TargetClusterColumn
        v-model="item.target_cluster"
        :cluster="item.cluster"
        :selected="selectedTargetClusters" />
      <BackupSourceColumn
        v-model="item.backup_source"
        @batch-edit="handleBatchEdit" />
      <BackupModeColumn
        v-model="item.rollback"
        :row-data="item"
        @batch-edit="handleBatchEdit" />
      <DbNameColumn
        v-model="item.databases"
        allow-asterisk
        check-not-exist
        :cluster-id="item.cluster.id"
        field="databases"
        :label="t('回档DB')"
        required
        @batch-edit="handleBatchEdit" />
      <DbNameColumn
        v-model="item.databases_ignore"
        check-exist
        :cluster-id="item.cluster.id"
        field="databases_ignore"
        :label="t('忽略DB')"
        @batch-edit="handleBatchEdit" />
      <DbNameColumn
        v-model="item.tables"
        allow-asterisk
        :cluster-id="item.cluster.id"
        field="tables"
        :label="t('回档表名')"
        required
        @batch-edit="handleBatchEdit" />
      <DbNameColumn
        v-model="item.tables_ignore"
        :cluster-id="item.cluster.id"
        field="tables_ignore"
        :label="t('忽略表名')"
        @batch-edit="handleBatchEdit" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { type Mysql } from '@services/model/ticket/ticket';
  import type { BackupLogRecord } from '@services/source/fixpointRollback';

  import { ClusterTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';

  import { random } from '@utils';

  import BackupModeColumn, { ROLLBACK_TYPE } from '../backup-mode-column/Index.vue';
  import BackupSourceColumn, { BACKUP_SOURCE } from '../backup-source-column/Index.vue';
  import ClusterColumn from '../ClusterColumn.vue';

  import TargetClusterColumn from './TargetClusterColumn.vue';

  interface RowData {
    backup_source: string;
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
    databases: string[];
    databases_ignore: string[];
    rollback: {
      backupid?: string;
      backupinfo?: BackupLogRecord;
      rollback_time?: string;
      rollback_type: string;
    };
    tables: string[];
    tables_ignore: string[];
    target_cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
  }

  interface Props {
    ticketDetails?: Mysql.ResourcePool.RollbackCluster;
  }

  interface Exposes {
    getValue: () => Promise<{
      infos: {
        backup_source: string;
        backupinfo?: BackupLogRecord; // 如果备份类型为REMOTE_AND_BACKUPID提供集群备份信息
        cluster_id: number;
        databases: string[];
        databases_ignore: string[];
        rollback_time?: string;
        rollback_type: string; // "REMOTE_AND_BACKUPID/REMOTE_AND_TIME"
        tables: string[];
        tables_ignore: string[];
        target_cluster_id: number;
      }[];
      rollback_cluster_type: 'BUILD_INTO_EXIST_CLUSTER';
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('待回档集群'),
    },
    {
      case: 'tendbha.test2.dba.db',
      key: 'target_master_domain',
      label: t('目标集群'),
    },
    {
      case: t('远程备份'),
      key: 'backup_source',
      label: t('备份源'),
    },
    {
      case: 'NULL',
      key: 'rollback',
      label: t('回档类型'),
    },
    {
      case: 'db1',
      key: 'databases',
      label: t('回档DB'),
    },
    {
      case: 'db2',
      key: 'databases_ignore',
      label: t('忽略DB'),
    },
    {
      case: 'tb1',
      key: 'tables',
      label: t('回档表名'),
    },
    {
      case: 'tb2',
      key: 'tables_ignore',
      label: t('忽略表名'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    backup_source: data.backup_source || BACKUP_SOURCE.REMOTE,
    cluster: Object.assign(
      {
        cluster_type: ClusterTypes.TENDBHA,
        id: 0,
        master_domain: '',
      },
      data.cluster,
    ),
    databases: data.databases || ['*'],
    databases_ignore: data.databases_ignore || [],
    rollback: Object.assign(
      {
        backupid: '',
        rollback_type: ROLLBACK_TYPE.BACKUPID,
      },
      data.rollback,
    ),
    tables: data.tables || ['*'],
    tables_ignore: data.tables_ignore || [],
    target_cluster: Object.assign(
      {
        cluster_type: ClusterTypes.TENDBHA,
        id: 0,
        master_domain: '',
      },
      data.target_cluster,
    ),
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const tableKey = ref(random());

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));
  const selectedTargetClusters = computed(() =>
    tableData.value.filter((item) => item.target_cluster.id).map((item) => item.target_cluster),
  );

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            const clusterInfo = clusters[item.cluster_id];
            const targetCluster = clusters[item.target_cluster_id];
            return createTableRow({
              backup_source: item.backup_source,
              cluster: {
                cluster_type: clusterInfo.cluster_type,
                id: item.cluster_id,
                master_domain: clusterInfo.immute_domain,
              },
              databases: item.databases,
              databases_ignore: item.databases_ignore,
              rollback: {
                backupid: item.backupinfo.backup_id,
                backupinfo: item.backupinfo,
                rollback_time: item.rollback_time,
                rollback_type: item.rollback_time ? ROLLBACK_TYPE.TIME : ROLLBACK_TYPE.BACKUPID,
              },
              tables: item.tables,
              tables_ignore: item.tables_ignore,
              target_cluster: {
                cluster_type: targetCluster.cluster_type,
                id: item.target_cluster_id,
                master_domain: targetCluster.immute_domain,
              },
            });
          });
        }
      }
    },
  );

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              cluster_type: item.cluster_type,
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        [field as keyof RowData]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        backup_source:
          item.backup_source === t('远程备份')
            ? BACKUP_SOURCE.REMOTE
            : item.backup_source === t('本地备份')
              ? BACKUP_SOURCE.LOCAL
              : '',
        cluster: {
          master_domain: item.master_domain,
        } as TendbhaModel,
        databases: item.databases ? [item.databases] : [],
        databases_ignore: item.databases_ignore ? [item.databases_ignore] : [],
        tables: item.tables ? [item.tables] : [],
        tables_ignore: item.tables_ignore ? [item.tables_ignore] : [],
        target_cluster: {
          master_domain: item.target_master_domain,
        } as TendbhaModel,
      }),
    );
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0].cluster.id ? tableData.value : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return {
          infos: [],
          rollback_cluster_type: 'BUILD_INTO_EXIST_CLUSTER',
        };
      }

      return {
        infos: tableData.value.map((item) => ({
          backup_source: item.backup_source,
          backupinfo: item.rollback.backupinfo,
          cluster_id: item.cluster.id,
          databases: item.databases,
          databases_ignore: item.databases_ignore,
          rollback_time: item.rollback.rollback_time,
          rollback_type: `${item.backup_source.toLocaleUpperCase()}_AND_${item.rollback.rollback_type}`,
          tables: item.tables,
          tables_ignore: item.tables_ignore,
          target_cluster_id: item.target_cluster.id,
        })),
        rollback_cluster_type: 'BUILD_INTO_EXIST_CLUSTER',
      };
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
