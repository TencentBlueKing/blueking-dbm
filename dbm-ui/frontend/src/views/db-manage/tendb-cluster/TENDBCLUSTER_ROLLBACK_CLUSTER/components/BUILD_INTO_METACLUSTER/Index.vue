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
  <EditableTable
    ref="table"
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="item.cluster"
        :selected="selected"
        @batch-edit="handleBatchEditCluster" />
      <BackupModeColumn
        v-model="item.rollback"
        :cluster="item.cluster"
        @batch-edit="handleBatchEdit" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';
  import type { BackupLogRecord } from '@services/source/fixpointRollback';

  import BackupModeColumn, { ROLLBACK_TYPE } from '../backup-mode-column/Index.vue';
  import ClusterColumn from '../ClusterColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
    };
    rollback: {
      backupid?: string;
      backupinfo?: BackupLogRecord;
      rollback_time?: string;
      rollback_type: string;
    };
  }

  interface Props {
    ticketDetails?: TendbCluster.ResourcePool.RollbackCluster;
  }

  interface Exposes {
    getValue: () => Promise<{
      infos: {
        backup_source: 'remote';
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
      rollback_cluster_type: 'BUILD_INTO_METACLUSTER';
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
    },
    rollback: data.rollback || {
      backupid: '',
      rollback_type: ROLLBACK_TYPE.REMOTE_AND_BACKUPID,
    },
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            const clusterInfo = clusters[item.cluster_id];
            return createTableRow({
              cluster: {
                id: item.cluster_id,
                master_domain: clusterInfo.immute_domain,
              },
              rollback: {
                backupid: item.backupinfo.backup_id,
                backupinfo: item.backupinfo,
                rollback_time: item.rollback_time,
                rollback_type: item.rollback_time ? ROLLBACK_TYPE.REMOTE_AND_TIME : ROLLBACK_TYPE.REMOTE_AND_BACKUPID,
              },
            });
          });
        }
      }
    },
  );

  const handleBatchEditCluster = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
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
        [field]: value,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return {
          infos: [],
          rollback_cluster_type: 'BUILD_INTO_METACLUSTER',
        };
      }

      return {
        infos: tableData.value.map((item) => ({
          backup_source: 'remote',
          backupinfo: item.rollback.backupinfo,
          cluster_id: item.cluster.id,
          databases: ['*'],
          databases_ignore: [],
          rollback_time: item.rollback.rollback_time,
          rollback_type: item.rollback.rollback_type,
          tables: ['*'],
          tables_ignore: [],
          target_cluster_id: item.cluster.id,
        })),
        rollback_cluster_type: 'BUILD_INTO_METACLUSTER',
      };
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
