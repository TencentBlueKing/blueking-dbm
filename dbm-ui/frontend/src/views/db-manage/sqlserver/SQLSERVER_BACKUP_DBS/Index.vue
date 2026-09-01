<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <BkAlert
        class="mb-16"
        closable
        theme="info"
        :title="t('数据库备份：指定DB备份，支持模糊匹配')" />
      <BatchInput
        class="mt-16"
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          :model="formData.tableData">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit"
              @request-success="() => handleClusterRequestSuccess(rowData)" />
            <DbNameColumn
              v-model="rowData.db_list"
              check-not-exist
              :cluster-id="rowData.cluster?.id"
              field="db_list"
              :label="t('备份 DB 名')"
              @batch-edit="handleDbTableBatchEdit" />
            <DbNameColumn
              v-model="rowData.ignore_db_list"
              :allow-asterisk="false"
              field="ignore_db_list"
              :label="t('忽略 DB 名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <FinalDbColumn
              v-model="rowData.backup_dbs"
              v-model:db-list="rowData.db_list"
              v-model:ignore-db-list="rowData.ignore_db_list"
              :cluster="rowData.cluster" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <BkFormItem
          class="mt-16"
          :label="t('备份方式')"
          property="backup_type"
          required>
          <BkRadioGroup
            v-model="formData.backup_type"
            size="small">
            <BkRadio label="full_backup">
              {{ t('全量备份') }}
            </BkRadio>
            <BkRadio label="log_backup">
              {{ t('增量备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('备份位置')"
          property="backup_place"
          required>
          <BkSelect
            v-model="formData.backup_place"
            disabled
            :list="backupLocationList"
            style="width: 360px" />
        </BkFormItem>
        <BkFormItem
          :label="t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup
            v-model="formData.file_tag"
            size="small">
            <template v-if="isBackupTypeFull">
              <BkRadio label="DBFILE1M"> {{ t('1个月') }} </BkRadio>
              <BkRadio label="DBFILE6M"> {{ t('6个月') }} </BkRadio>
              <BkRadio label="DBFILE1Y"> {{ t('1年') }} </BkRadio>
              <BkRadio label="DBFILE3Y"> {{ t('3年') }} </BkRadio>
            </template>
            <template v-else>
              <BkRadio label="INCREMENT_BACKUP"> 15 {{ t('天') }} </BkRadio>
            </template>
          </BkRadioGroup>
        </BkFormItem>
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
  import { getIgnoreDbs } from '@services/source/sqlserverCluster';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/sqlserver/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import { random } from '@utils';

  import FinalDbColumn from './components/FinalDbColumn.vue';

  interface IDataRow {
    backup_dbs: string[];
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
    db_list: string[];
    ignore_db_list: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    backup_dbs: values.backup_dbs || ([] as string[]),
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    db_list: values.db_list || ([] as string[]),
    ignore_db_list: values.ignore_db_list || ([] as string[]),
  });

  const createDefaultFormData = () => ({
    backup_place: 'master',
    backup_type: 'full_backup',
    file_tag: 'DBFILE1M',
    payload: createTicketPayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Sqlserver.BackupDb>(TicketTypes.SQLSERVER_BACKUP_DBS, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      isTicketLoaded = true;
      Object.assign(formData, {
        backup_place: details.backup_place,
        backup_type: details.backup_type,
        file_tag: details.file_tag,
        payload: createTicketPayload(ticketDetail),
        remark,
        tableData: details.infos.map((item) =>
          createRowData({
            cluster: {
              master_domain: details.clusters[item.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            db_list: item.db_list,
            ignore_db_list: item.ignore_db_list,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_place: string;
    backup_type: string;
    file_tag: string;
    infos: {
      backup_dbs: string[];
      cluster_id: number;
      db_list: string[];
      ignore_db_list: string[];
    }[];
  }>(TicketTypes.SQLSERVER_BACKUP_DBS);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');
  const tableKey = ref(random());
  let isTicketLoaded = false;

  const backupLocationList = [
    {
      label: t('主库主机'),
      value: 'master',
    },
  ];

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const isBackupTypeFull = computed(() => formData.backup_type === 'full_backup');

  const handleClusterRequestSuccess = async (rowData: IDataRow) => {
    if (isTicketLoaded) {
      isTicketLoaded = false;
      return;
    }
    const ingoreDbsMap = await getIgnoreDbs({
      cluster_ids: [rowData.cluster.id],
    });
    Object.assign(rowData, {
      ignore_db_list: ingoreDbsMap?.[rowData.cluster.id] || [],
    });
  };

  const batchInputConfig = [
    {
      case: 'sqlserver.test.dba.db',
      key: 'domain',
      label: t('集群域名'),
    },
    {
      case: 'db1,db2',
      key: 'db_list',
      label: t('备份 DB 名'),
    },
    {
      case: 'ignore_db1,ignore_db2',
      key: 'ignore_db_list',
      label: t('忽略 DB 名'),
    },
  ];

  const handleClusterBatchEdit = async (data: SqlserverHaModel[]) => {
    // 过滤出未选择的集群
    const newClusters = data.filter((item) => !selectedMap.value[item.master_domain]);
    if (newClusters.length === 0) return;

    const clusterIds = newClusters.map((item) => item.id);
    const ingoreDbsMap = await getIgnoreDbs({ cluster_ids: clusterIds });

    const dataList = newClusters.map((item) =>
      createRowData({
        cluster: {
          cluster_type: item.cluster_type,
          id: item.id,
          master_domain: item.master_domain,
        },
        ignore_db_list: ingoreDbsMap?.[item.id] || [],
      }),
    );
    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...dataList];
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
        db_list: item.db_list ? item.db_list.split(',') : [],
        ignore_db_list: item.ignore_db_list ? item.ignore_db_list.split(',') : [],
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
            backup_dbs: item.backup_dbs,
            cluster_id: item.cluster?.id,
            db_list: item.db_list,
            ignore_db_list: item.ignore_db_list,
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
