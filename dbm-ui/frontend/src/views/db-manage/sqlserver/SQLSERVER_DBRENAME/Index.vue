<template>
  <div class="sqlserver-toolbox-db-rename-page">
    <SmartAction>
      <BkAlert
        closable
        theme="info"
        :title="t('DB 重命名：database 重命名')" />
      <BatchInput
        class="mt-16"
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical">
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
            <DbNameColumn
              v-model="rowData.from_database"
              check-not-exist
              :cluster-id="rowData.cluster.id"
              field="from_database"
              :label="t('原 DB 名')"
              single
              @batch-edit="handleDbTableBatchEdit" />
            <DbNameColumn
              v-model="rowData.to_database"
              check-exist
              :cluster-id="rowData.cluster.id"
              field="to_database"
              :label="t('新 DB 名')"
              single
              @batch-edit="handleDbTableBatchEdit" />
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

  import { random } from '@utils';

  interface IDataRow {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
    from_database: string[];
    to_database: string[];
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
    from_database: values.from_database || ([] as string[]),
    to_database: values.to_database || ([] as string[]),
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Sqlserver.DbRename>(TicketTypes.SQLSERVER_DBRENAME, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createRowData({
            cluster: {
              master_domain: details.clusters[item.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            from_database: [item.from_database],
            to_database: [item.to_database],
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      from_database: string;
      to_database: string;
    }[];
  }>(TicketTypes.SQLSERVER_DBRENAME);

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

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const batchInputConfig = [
    {
      case: 'sqlserver.test.dba.db',
      key: 'domain',
      label: t('集群域名'),
    },
    {
      case: 'db1,db2',
      key: 'from_database',
      label: t('原 DB 名'),
    },
    {
      case: 'new_db1,new_db2',
      key: 'to_database',
      label: t('新 DB 名'),
    },
  ];

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

  const handleDbTableBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
        from_database: item.from_database ? item.from_database.split(',') : [],
        to_database: item.to_database ? item.to_database.split(',') : [],
      }),
    );

    if (isClear) {
      tableKey.value = random();
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
          ...formData,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster?.id,
            from_database: item.from_database[0],
            to_database: item.to_database[0],
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
