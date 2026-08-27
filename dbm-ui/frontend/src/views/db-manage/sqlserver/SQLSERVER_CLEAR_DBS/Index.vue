<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <BkAlert
        closable
        theme="info"
        :title="
          t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')
        " />
      <BatchInput
        class="mt-20"
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
              :selected="selected"
              :tab-list-config="clusterSelectorTabConfig"
              @batch-edit="handleClusterBatchEdit" />
            <ClearModeColumn
              v-model="rowData.clean_mode"
              @batch-edit="handleColumnBatchEdit" />
            <DbNameColumn
              v-model="rowData.clean_dbs_patterns"
              check-not-exist
              :cluster-id="rowData.cluster?.id"
              field="clean_dbs_patterns"
              :label="t('指定DB名')"
              @batch-edit="handleColumnBatchEdit" />
            <DbNameColumn
              v-model="rowData.clean_ignore_dbs_patterns"
              :allow-asterisk="false"
              field="clean_ignore_dbs_patterns"
              :label="t('忽略DB名')"
              :required="false"
              @batch-edit="handleColumnBatchEdit" />
            <TableNameColumn
              v-model="rowData.clean_tables"
              :cluster-id="rowData.cluster?.id"
              :disabled="rowData.clean_mode === CLEAR_MODE.DROP_DBS"
              field="clean_tables"
              :label="t('指定表名')"
              @batch-edit="handleColumnBatchEdit" />
            <TableNameColumn
              v-model="rowData.ignore_clean_tables"
              :allow-asterisk="false"
              :cluster-id="rowData.cluster?.id"
              :disabled="rowData.clean_mode === CLEAR_MODE.DROP_DBS"
              field="ignore_clean_tables"
              :label="t('忽略表名')"
              :required="false"
              @batch-edit="handleColumnBatchEdit" />
            <FinalDbColumn
              v-model="rowData.clean_dbs"
              v-model:db-list="rowData.clean_dbs_patterns"
              v-model:ignore-db-list="rowData.clean_ignore_dbs_patterns"
              :cluster="rowData.cluster" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbResetButton
          class="ml-8"
          :confirm-handler="handleReset"
          :disabled="isSubmitting" />
      </template>
    </SmartAction>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/sqlserver/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/table-name-column/Index.vue';

  import { random } from '@utils';

  import ClearModeColumn, { CLEAR_MODE } from './components/ClearModeColumn.vue';
  import FinalDbColumn from './components/FinalDbColumn.vue';

  interface IDataRow {
    clean_dbs: string[];
    clean_dbs_patterns: string[];
    clean_ignore_dbs_patterns: string[];
    clean_mode: string;
    clean_tables: string[];
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
    ignore_clean_tables: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    clean_dbs: values.clean_dbs || ([] as string[]),
    clean_dbs_patterns: values.clean_dbs_patterns || ([] as string[]),
    clean_ignore_dbs_patterns: values.clean_ignore_dbs_patterns || ([] as string[]),
    clean_mode: values.clean_mode || '',
    clean_tables: values.clean_tables || ['*'],
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    ignore_clean_tables: values.ignore_clean_tables || ([] as string[]),
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Sqlserver.ClearDbs>(TicketTypes.SQLSERVER_CLEAR_DBS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createRowData({
            // clean_dbs: item.clean_dbs,
            clean_dbs_patterns: item.clean_dbs_patterns,
            clean_ignore_dbs_patterns: item.clean_ignore_dbs_patterns,
            clean_mode: item.clean_mode,
            clean_tables: item.clean_tables,
            cluster: {
              master_domain: details.clusters[item.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            ignore_clean_tables: item.ignore_clean_tables,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      clean_dbs: string[];
      clean_dbs_patterns: string[];
      clean_ignore_dbs_patterns: string[];
      clean_mode: string;
      clean_tables: string[];
      cluster_id: number;
      ignore_clean_tables: string[];
    }[];
  }>(TicketTypes.SQLSERVER_CLEAR_DBS);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

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

  const formData = reactive(createDefaultFormData());
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'sqlserver.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
    {
      case: t('清理表数据'),
      key: 'clean_mode',
      label: t('清档类型'),
      values: [t('清理表数据'), t('删除表'), t('删除整库')],
    },
    {
      case: 'db1,db2',
      key: 'clean_dbs_patterns',
      label: t('指定 DB 名'),
    },
    {
      case: 'NULL',
      key: 'clean_ignore_dbs_patterns',
      label: t('忽略 DB 名'),
    },
    {
      case: 'table1,table2',
      key: 'clean_tables',
      label: t('指定表名'),
    },
    {
      case: 'NULL',
      key: 'ignore_clean_tables',
      label: t('忽略表名'),
    },
  ];

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: SqlserverHaModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
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
    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...newList];
  };

  const handleColumnBatchEdit = (value: string[] | string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        clean_dbs_patterns: item.clean_dbs_patterns ? item.clean_dbs_patterns.split(',') : [],
        clean_ignore_dbs_patterns: item.clean_ignore_dbs_patterns ? item.clean_ignore_dbs_patterns.split(',') : [],
        clean_mode: item.clean_mode || '',
        clean_tables: item.clean_tables ? item.clean_tables.split(',') : ['*'],
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
        ignore_clean_tables: item.ignore_clean_tables ? item.ignore_clean_tables.split(',') : [],
      }),
    );

    tableKey.value = random();
    if (isClear) {
      formData.tableData = dataList;
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...dataList];
    }
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    editableTableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            clean_dbs: item.clean_dbs,
            clean_dbs_patterns: item.clean_dbs_patterns,
            clean_ignore_dbs_patterns: item.clean_ignore_dbs_patterns,
            clean_mode: item.clean_mode,
            clean_tables: item.clean_tables,
            cluster_id: item.cluster?.id,
            ignore_clean_tables: item.ignore_clean_tables,
          })),
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>
<style lang="less">
  .sqlserver-db-backup-page {
    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
