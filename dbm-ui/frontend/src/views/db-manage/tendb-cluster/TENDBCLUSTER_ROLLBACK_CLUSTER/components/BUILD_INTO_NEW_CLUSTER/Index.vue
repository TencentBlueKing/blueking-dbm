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
      <MultipleResourceHostColumn
        v-model="item.remote_hosts"
        field="remote_hosts"
        :label="t('存储层主机')"
        :min-width="200"
        :params="{
          resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
        }" />
      <SingleResourceHostColumn
        v-model="item.spider_host"
        field="spider_host.ip"
        :label="t('接入层主机')"
        :min-width="200"
        :params="{
          resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
        }" />
      <BackupModeColumn
        v-model="item.rollback"
        :cluster="item.cluster"
        @batch-edit="handleBatchEdit" />
      <TagDbNameColumn
        v-model="item.databases"
        allow-asterisk
        check-exist
        :cluster-id="item.cluster.id"
        field="databases"
        :label="t('回档DB')"
        required
        @batch-edit="handleBatchEdit" />
      <TagDbNameColumn
        v-model="item.databases_ignore"
        check-exist
        :cluster-id="item.cluster.id"
        field="databases_ignore"
        :label="t('忽略DB')"
        @batch-edit="handleBatchEdit" />
      <TagDbNameColumn
        v-model="item.tables"
        allow-asterisk
        check-exist
        :cluster-id="item.cluster.id"
        field="tables"
        :label="t('回档表名')"
        required
        @batch-edit="handleBatchEdit" />
      <TagDbNameColumn
        v-model="item.tables_ignore"
        check-exist
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
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { BackupLogRecord } from '@services/source/fixpointRollback';

  import { DBTypes } from '@common/const';

  import MultipleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/multiple-resource-host-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import TagDbNameColumn from '@views/db-manage/common/toolbox-field/column/tag-db-name-column/Index.vue';

  import BackupModeColumn, { ROLLBACK_TYPE } from '../backup-mode-column/Index.vue';
  import ClusterColumn from '../ClusterColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
    };
    // 存储层
    remote_hosts: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    // 接入层
    spider_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    rollback: {
      rollback_type: string;
      backupid?: string;
      backupinfo?: BackupLogRecord;
      rollback_time?: string;
    };
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
  }

  interface Props {
    data: RowData[];
  }

  interface Exposes {
    getValue: () => Promise<{
      rollback_cluster_type: 'BUILD_INTO_NEW_CLUSTER';
      ip_source: 'resource_pool'; // 只有在回档新集群选项，才传递此参数
      infos: {
        cluster_id: number;
        resource_spec: {
          remote_hosts: {
            spec_id: number;
            count: number;
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
          };
          spider_host: {
            spec_id: number;
            count: number;
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
          };
        };
        backup_source: 'remote';
        rollback_type: string; // "REMOTE_AND_BACKUPID/REMOTE_AND_TIME"
        rollback_time?: string;
        backupinfo?: BackupLogRecord; // 如果备份类型为REMOTE_AND_BACKUPID提供集群备份信息
        databases: string[];
        databases_ignore: string[];
        tables: string[];
        tables_ignore: string[];
      }[];
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
    },
    remote_hosts: data.remote_hosts || [],
    spider_host: data.spider_host || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
    rollback: data.rollback || {
      rollback_type: ROLLBACK_TYPE.REMOTE_AND_BACKUPID,
    },
    databases: data.databases || ['*'],
    databases_ignore: data.databases_ignore || [],
    tables: data.tables || ['*'],
    tables_ignore: data.tables_ignore || [],
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  watch(
    () => props.data,
    () => {
      if (props.data.length) {
        tableData.value = [...props.data];
      } else {
        tableData.value = [createTableRow()];
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
      item[field as keyof RowData] = value;
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return {
          rollback_cluster_type: 'BUILD_INTO_NEW_CLUSTER',
          ip_source: 'resource_pool',
          infos: [],
        };
      }

      return {
        rollback_cluster_type: 'BUILD_INTO_NEW_CLUSTER',
        ip_source: 'resource_pool',
        infos: tableData.value.map((item) => ({
          cluster_id: item.cluster.id,
          resource_spec: {
            remote_hosts: {
              spec_id: 0,
              count: item.remote_hosts.length,
              hosts: item.remote_hosts,
            },
            spider_host: {
              spec_id: 0,
              count: 1,
              hosts: [item.spider_host],
            },
          },
          backup_source: 'remote',
          rollback_type: item.rollback.rollback_type,
          rollback_time: item.rollback.rollback_time,
          backupinfo: item.rollback.backupinfo,
          databases: item.databases,
          databases_ignore: item.databases_ignore,
          tables: item.tables,
          tables_ignore: item.tables_ignore,
        })),
      };
    },
  });
</script>
