<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <BkAlert
        closable
        theme="info"
        :title="
          t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')
        " />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mb-16"
          :model="formData.tableData"
          :rules="rules">
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
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="ml8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </div>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/sqlserver/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/table-name-column/Index.vue';

  import ClearModeColumn, { CLEAR_MODE } from './components/ClearModeColumn.vue';
  import FinalDbColumn from './components/FinalDbColumn.vue';

  interface IDataRow {
    clean_dbs: string[];
    clean_dbs_patterns: string[];
    clean_ignore_dbs_patterns: string[];
    clean_mode: string;
    clean_tables: string[];
    cluster: {
      cluster_type: string;
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
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Sqlserver.ClearDbs>(TicketTypes.SQLSERVER_CLEAR_DBS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
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

  const rules = {
    'cluster.master_domain': [
      {
        message: t('目标集群重复'),
        trigger: 'change',
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = formData.tableData.filter((row) => row.cluster.master_domain === value);
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

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterColumn>['selected'] = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
    };
    formData.tableData.forEach((tableRow) => {
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
    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleColumnBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
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
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
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
