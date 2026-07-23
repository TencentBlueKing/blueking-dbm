<template>
  <BatchInput
    class="mb-20"
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
    ref="editableTable"
    class="mb-12"
    :model="tableData">
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
      <DstClusterColumn
        v-model="rowData.dst_cluster"
        :src-cluster-data="rowData.cluster as any"
        @batch-edit="handleDstClusterBatchEdit" />
      <RenderModeColumn
        ref="renderModeColumnRef"
        v-model:restore-backup-file="rowData.restore_backup_file as any"
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
        :is-local="false"
        :restore-backup-file="rowData.restore_backup_file as any"
        :restore-time="rowData.restore_time"
        :target-cluster-id="rowData.dst_cluster.id" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useTimeZoneFormat } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import ClusterColumn from '@views/db-manage/sqlserver/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import { random } from '@utils';

  import FinalDbColumn from '../common/final-db-column/Index.vue';
  import RenderModeColumn from '../common/render-mode-column/Index.vue';

  import DstClusterColumn from './components/DstClusterColumn.vue';

  interface Expose {
    reset: () => void;
    setTicketCloneData: (details: Sqlserver.Rollback) => void;
    submit: () => Promise<any>;
  }

  interface IDataRow {
    cluster: {
      bk_cloud_id: number;
      cluster_type: ClusterTypes;
      id: number;
      major_version: string;
      master_domain: string;
    };
    db_list: string[];
    dst_cluster: {
      bk_cloud_id: number;
      id: number;
      major_version: string;
      master_domain: string;
    };
    ignore_db_list: string[];
    rename_infos: {
      db_name: string;
      old_db_name: string;
      rename_db_name: string;
      target_db_name: string;
    }[];
    restore_backup_file: {
      backup_id: string;
      logs: {
        backup_begin_time: string;
        backup_end_time: string;
        backup_host: string;
        backup_id: string;
        backup_port: number;
        backup_task_end_time: string;
        backup_task_start_time: string;
        backup_type: string;
        bill_id: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        charset: string;
        checkpointlsn: number;
        cluster_address: string;
        cluster_id: number;
        compatibility_level: number;
        data_schema_grant: string;
        databasebackuplsn: number;
        db_list: string;
        db_size_kb: number;
        dbname: string;
        file_cnt: number;
        file_name: string;
        file_size_kb: number;
        firstlsn: number;
        is_full_backup: boolean;
        lastlsn: number;
        local_path: string;
        master_ip: string;
        master_port: number;
        role: string;
        task_id: string;
        time_zone: string;
        version: string;
      }[];
    };
    restore_time: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_type: '',
        id: 0,
        major_version: '',
        master_domain: '',
      },
      values.cluster,
    ),
    db_list: values.db_list || [],
    dst_cluster: Object.assign(
      {
        bk_cloud_id: 0,
        id: 0,
        major_version: '',
        master_domain: '',
      },
      values.dst_cluster,
    ),
    ignore_db_list: values.ignore_db_list || [],
    rename_infos: values.rename_infos || [],
    restore_backup_file: values.restore_backup_file || [],
    restore_time: values.restore_time || '',
  });

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const editableTableRef = useTemplateRef('editableTable');
  const renderModeColumnRef = useTemplateRef<Array<InstanceType<typeof RenderModeColumn>>>('renderModeColumnRef');
  const tableKey = ref(random());

  // const rules = {
  //   'cluster.master_domain': [
  //     {
  //       message: t('目标集群重复'),
  //       trigger: 'change',
  //       validator: (value: string) => {
  //         if (value) {
  //           const nonEmptyIdList = tableData.value.filter((row) => row.cluster.master_domain === value);
  //           return nonEmptyIdList.length === 1;
  //         }
  //         return true;
  //       },
  //     },
  //   ],
  // };

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

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const batchInputConfig = [
    {
      case: 'sqlserver.test.dba.db',
      key: 'master_domain',
      label: t('待回档集群'),
    },
    {
      case: 'sqlserver.test.dba.db',
      key: 'dst_master_domain',
      label: t('目标集群'),
    },
    {
      case: 'NULL',
      key: 'rollback',
      label: t('回档类型'),
    },
    {
      case: 'db1,db2',
      key: 'db_list',
      label: t('构造 DB'),
    },
    {
      case: 'db1,db2',
      key: 'ignore_db_list',
      label: t('忽略 DB'),
    },
  ];

  const handleClusterBatchEdit = (clusterList: SqlserverHaModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
            },
          }) as IDataRow,
        );
      }
    });
    tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...newList];
  };

  const handleDstClusterBatchEdit = (value: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item.dst_cluster, {
        bk_cloud_id: 0,
        id: 0,
        major_version: '',
        master_domain: value,
      });
    });
  };

  const handleDbTableBatchEdit = (value: string[], field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
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
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        cluster: {
          master_domain: item.master_domain,
        } as IDataRow['cluster'],
        db_list: item.db_list ? item.db_list.split(',') : [],
        dst_cluster: {
          master_domain: item.dst_master_domain,
        } as IDataRow['dst_cluster'],
        ignore_db_list: item.ignore_db_list ? item.ignore_db_list.split(',') : [],
      }),
    );

    tableKey.value = random();
    if (isClear) {
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...dataList];
    }
  };
  defineExpose<Expose>({
    reset() {
      tableData.value = [createRowData()];
    },
    setTicketCloneData(details: Sqlserver.Rollback) {
      const { clusters, infos } = details;
      tableData.value = infos.map((infoItem) => {
        return createRowData({
          cluster: {
            bk_cloud_id: clusters[infoItem.src_cluster].bk_cloud_id,
            cluster_type: clusters[infoItem.src_cluster].cluster_type,
            id: infoItem.src_cluster,
            major_version: clusters[infoItem.src_cluster].major_version,
            master_domain: clusters[infoItem.src_cluster].immute_domain,
          } as IDataRow['cluster'],
          db_list: infoItem.db_list || [],
          dst_cluster: {
            bk_cloud_id: clusters[infoItem.dst_cluster].bk_cloud_id,
            id: infoItem.dst_cluster,
            major_version: clusters[infoItem.dst_cluster].major_version,
            master_domain: clusters[infoItem.dst_cluster].immute_domain,
          } as IDataRow['dst_cluster'],
          ignore_db_list: infoItem.ignore_db_list || [],
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
            dst_cluster: rowData.dst_cluster.id,
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
