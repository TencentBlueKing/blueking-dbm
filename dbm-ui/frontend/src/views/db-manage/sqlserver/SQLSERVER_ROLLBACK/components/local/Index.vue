<template>
  <EditableTable
    ref="editableTable"
    class="mb-12"
    :model="tableData"
    :rules="rules">
    <EditableRow
      v-for="(rowData, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="rowData.cluster"
        :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
        :label="t('待回档集群')"
        :selected="selected"
        :tab-list-config="clusterSelectorTabConfig"
        @batch-edit="handleClusterBatchEdit" />
      <RenderModeColumn
        ref="renderModeColumnRef"
        v-model:restore-backup-file="rowData.restore_backup_file"
        v-model:restore-time="rowData.restore_time"
        :cluster-id="rowData.cluster.id"
        @batch-edit="handleRenderModeBatchEdit" />
      <DbNameColumn
        v-model="rowData.db_list"
        check-not-exist
        :cluster-id="rowData.cluster?.id"
        field="db_list"
        :label="t('构造 DB')"
        @batch-edit="handleDbTableBatchEdit" />
      <DbNameColumn
        v-model="rowData.ignore_db_list"
        :allow-asterisk="false"
        field="ignore_db_list"
        :label="t('忽略 DB')"
        :required="false"
        @batch-edit="handleDbTableBatchEdit" />
      <FinalDbColumn
        v-model="rowData.rename_infos"
        v-model:db-ignore-name="rowData.ignore_db_list"
        v-model:db-name="rowData.db_list"
        :cluster="rowData.cluster"
        is-local
        :restore-backup-file="rowData.restore_backup_file"
        :restore-time="rowData.restore_time"
        :target-cluster-id="rowData.cluster.id" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useTimeZoneFormat } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterColumn from '@views/db-manage/sqlserver/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import FinalDbColumn from '../common/FinalDbColumn.vue';
  import RenderModeColumn from '../common/render-mode-column/Index.vue';

  interface Expose {
    reset: () => void;
    setTicketCloneData: (details: Sqlserver.Rollback) => void;
    submit: () => Promise<any>;
  }

  interface IDataRow {
    cluster: {
      cluster_type: string;
      id: number;
      master_domain: string;
    };
    db_list: string[];
    ignore_db_list: string[];
    rename_infos: {
      db_name: string;
      old_db_name: string;
      rename_db_name: string;
      target_db_name: string;
    }[];
    restore_backup_file: {
      backup_id: string;
      complete: boolean;
      end_time: string;
      expected_cnt: number;
      logs: Record<string, string>[];
      real_cnt: number;
      role: string;
      start_time: string;
    };
    restore_time: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    db_list: values.db_list || [],
    ignore_db_list: values.ignore_db_list || [],
    rename_infos: values.rename_infos || [],
    restore_backup_file: Object.assign(
      {
        backup_id: '',
        complete: false,
        end_time: '',
        expected_cnt: 0,
        logs: {},
        real_cnt: 0,
        role: '',
        start_time: '',
      },
      values.restore_backup_file,
    ),
    restore_time: values.restore_time || '',
  });

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const editableTableRef = useTemplateRef('editableTable');
  const renderModeColumnRef = useTemplateRef<Array<InstanceType<typeof RenderModeColumn>>>('renderModeColumnRef');

  const rules = {
    'cluster.master_domain': [
      {
        message: t('目标集群重复'),
        trigger: 'change',
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = tableData.value.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
      },
    ],
  };

  const clusterSelectorTabConfig = {
    [ClusterTypes.SQLSERVER_HA]: {
      disabledRowConfig: [
        {
          handler: (data: any) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      id: ClusterTypes.SQLSERVER_HA,
      name: t('SqlServer 主从'),
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      disabledRowConfig: [
        {
          handler: (data: any) => data.isOffline,
          tip: t('集群已禁用'),
        },
      ],
      id: ClusterTypes.SQLSERVER_SINGLE,
      name: t('SqlServer 单节点'),
    },
  };

  const tableData = ref([createRowData()]);

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterColumn>['selected'] = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
    };
    tableData.value.forEach((tableRow) => {
      const { cluster_type: clusterType, id, master_domain: masterDomain } = tableRow.cluster;
      if (id) {
        selectedClusters[clusterType as keyof typeof selectedClusters].push({
          id,
          master_domain: masterDomain,
        });
      }
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const handleClusterBatchEdit = (clusterList: SqlserverHaModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });
    tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const handleDbTableBatchEdit = (value: string[], field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleRenderModeBatchEdit = (
    value: {
      time: string;
      type: string;
    },
    field: string,
  ) => {
    if (value.type === 'time') {
      tableData.value.forEach((item) => {
        Object.assign(item, {
          [field]: value.time,
        });
      });
    } else {
      tableData.value.forEach((item) => {
        Object.assign(item, {
          restore_time: '',
        });
      });
      renderModeColumnRef.value!.forEach((refItem) => refItem.setRecordByBatch(value.time));
    }
    window.changeConfirm = true;
  };

  defineExpose<Expose>({
    reset() {
      tableData.value = [createRowData()];
      window.changeConfirm = false;
    },
    setTicketCloneData(details: Sqlserver.Rollback) {
      const { clusters, infos } = details;
      tableData.value = infos.map((infoItem) => {
        return createRowData({
          cluster: {
            master_domain: clusters[infoItem.src_cluster].immute_domain,
          } as IDataRow['cluster'],
          db_list: infoItem.db_list,
          ignore_db_list: infoItem.ignore_db_list,
          rename_infos: infoItem.rename_infos,
          restore_backup_file: infoItem.restore_backup_file,
          restore_time: infoItem.restore_time,
        });
      });
    },
    async submit() {
      const validateResult = await editableTableRef.value!.validate();
      if (validateResult) {
        return tableData.value.map((rowData) => {
          const info = {
            db_list: rowData.db_list,
            dst_cluster: rowData.cluster.id,
            ignore_db_list: rowData.ignore_db_list,
            rename_infos: rowData.rename_infos,
            src_cluster: rowData.cluster.id,
          };
          if (rowData.restore_time) {
            Object.assign(info, {
              restore_time: formatDateToUTC(rowData.restore_time),
            });
          } else {
            Object.assign(info, {
              restore_backup_file: rowData.restore_backup_file,
            });
          }
          return info;
        });
      }
    },
  });
</script>
<style lang="less">
  .sqlserver-rollback-page {
    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
