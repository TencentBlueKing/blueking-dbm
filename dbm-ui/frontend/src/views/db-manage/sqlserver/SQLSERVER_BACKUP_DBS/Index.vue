<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <BkAlert
        closable
        theme="info"
        :title="t('数据库备份：指定DB备份，支持模糊匹配')" />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          :model="formData.tableData"
          :rules="rules">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
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

  import FinalDbColumn from './components/FinalDbColumn.vue';

  interface IDataRow {
    backup_dbs: string[];
    cluster: {
      cluster_type: string;
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
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Sqlserver.BackupDb>(TicketTypes.SQLSERVER_BACKUP_DBS, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      Object.assign(formData, {
        backup_place: details.backup_place,
        backup_type: details.backup_type,
        file_tag: details.file_tag,
        payload: createTickePayload(ticketDetail),
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

  const backupLocationList = [
    {
      label: t('主库主机'),
      value: 'master',
    },
  ];

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

  const isBackupTypeFull = computed(() => formData.backup_type === 'full_backup');

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

  const handleDbTableBatchEdit = (value: string[], field: string) => {
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
