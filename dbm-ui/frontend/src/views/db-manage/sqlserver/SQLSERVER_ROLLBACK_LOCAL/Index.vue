<template>
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('在选择原集群上进行原地数据回滚，支持指定备份记录或指定时间进行回档')" />
    <DbForm
      ref="formRef"
      class="mb-24 toolbox-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('时区')"
        required>
        <TimeZonePicker style="width: 450px" />
      </BkFormItem>
      <BkFormItem
        :label="t('回档方式')"
        required>
        <CardCheckbox
          v-model="formData.rollbackMethod"
          :desc="t('使用备份文件构造数据')"
          icon="bk-dbm-icon db-icon-form"
          :title="t('指定备份记录回档')"
          true-value="BACKUPID" />
        <CardCheckbox
          v-model="formData.rollbackMethod"
          class="ml-8"
          :desc="t('使用指定的时间最近的备份构造数据')"
          icon="bk-dbm-icon db-icon-time"
          :title="t('指定时间回档')"
          true-value="TIME" />
      </BkFormItem>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="editableTableRef"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            allow-repeat
            :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
            :label="t('源集群')"
            :selected="selected"
            :tab-list-config="clusterSelectorTabConfig"
            @batch-edit="handleClusterBatchEdit" />
          <BackupRecordColumn
            v-if="formData.rollbackMethod === 'BACKUPID'"
            v-model="item.backupRecord"
            v-model:table-data="formData.tableData"
            :cluster="item.cluster" />
          <TimeBackupRecordColumn
            v-if="formData.rollbackMethod === 'TIME'"
            ref="timeBackupRecordColumnRef"
            v-model:backup-record="item.backupRecord"
            v-model:backup-time="item.backupTime"
            v-model:table-data="formData.tableData"
            :cluster="item.cluster" />
          <DbNameColumn
            v-model="item.databases"
            allow-asterisk
            :cluster-id="item.cluster?.id"
            field="databases"
            :label="t('恢复库')"
            required
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.databasesIgnore"
            :allow-asterisk="false"
            :cluster-id="item.cluster?.id"
            field="databasesIgnore"
            :label="t('忽略库')"
            :required="false"
            @batch-edit="handleBatchEdit" />
          <FinalDbColumn
            ref="finalDbColumnRef"
            v-model="item.renameInfos"
            v-model:db-ignore-name="item.databasesIgnore"
            v-model:db-name="item.databases"
            :cluster="item.cluster"
            is-local
            :restore-backup-file="item.backupRecord"
            :restore-time="item.backupTime"
            :target-cluster="item.cluster" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </DbForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SqlserverBackupLogModel from '@services/model/sqlserver/backup-log';
  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/sqlserver/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';
  import BackupRecordColumn from '@views/db-manage/sqlserver/SQLSERVER_ROLLBACK/components/backup-record-column/Index.vue';
  import FinalDbColumn from '@views/db-manage/sqlserver/SQLSERVER_ROLLBACK/components/final-db-column/Index.vue';
  import TimeBackupRecordColumn from '@views/db-manage/sqlserver/SQLSERVER_ROLLBACK/components/time-backup-record-column/Index.vue';

  import { random } from '@utils';

  interface RenameInfo {
    db_name: string;
    rename_db_name: string;
    target_db_name: string;
  }

  interface RowData {
    backupRecord: SqlserverBackupLogModel | undefined;
    backupTime: string;
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
    };
    databases: string[];
    databasesIgnore: string[];
    renameInfos: RenameInfo[];
  }

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();
  const router = useRouter();

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

  const batchInputConfig = computed(() => {
    const base = [
      {
        case: 'sqlserver.test.dba.db',
        key: 'master_domain',
        label: t('源集群'),
      },
      {
        case: 'NULL',
        key: 'backupRecord',
        label: t('备份记录'),
      },
      {
        case: 'db1,db2',
        key: 'databases',
        label: t('恢复库'),
      },
      {
        case: 'db3,db4',
        key: 'databasesIgnore',
        label: t('排除库'),
      },
    ];
    if (formData.rollbackMethod === 'TIME') {
      base.splice(1, 0, {
        case: '2025-08-24T23:59:59',
        key: 'backupTime',
        label: t('回档时间'),
      });
    }
    return base;
  });

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    backupRecord: (data.backupRecord ?? undefined) as SqlserverBackupLogModel | undefined,
    backupTime: data.backupTime || '',
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as RowData['cluster'],
      data.cluster,
    ),
    databases: (data.databases || []) as string[],
    databasesIgnore: (data.databasesIgnore || []) as string[],
    renameInfos: (data.renameInfos || []) as RenameInfo[],
  });

  const formRef = useTemplateRef('formRef');
  const editableTableRef = useTemplateRef('editableTableRef');
  const timeBackupRecordColumnRef =
    useTemplateRef<InstanceType<typeof TimeBackupRecordColumn>[]>('timeBackupRecordColumnRef');
  const finalDbColumnRef = useTemplateRef<InstanceType<typeof FinalDbColumn>[]>('finalDbColumnRef');

  const defaultData = () => ({
    payload: createTicketPayload(),
    rollbackMethod: 'BACKUPID',
    tableData: [createTableRow()],
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<Sqlserver.Rollback>(TicketTypes.SQLSERVER_ROLLBACK_LOCAL, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        rollbackMethod: infos[0].restore_time ? 'TIME' : 'BACKUPID',
      });
      nextTick(() => {
        formData.tableData = infos.map((item) =>
          createTableRow({
            backupRecord: item.restore_time
              ? undefined
              : (item.restore_backup_file as unknown as SqlserverBackupLogModel),
            backupTime: item.restore_time,
            cluster: {
              master_domain: clusters[item.src_cluster]?.immute_domain || '',
            },
            databases: item.db_list,
            databasesIgnore: item.ignore_db_list,
            renameInfos: item.rename_infos.map((ri) => ({
              db_name: ri.db_name,
              rename_db_name: ri.rename_db_name,
              target_db_name: ri.target_db_name,
            })),
          }),
        );
      }).then(() => {
        timeBackupRecordColumnRef.value?.[0]?.flush();
        finalDbColumnRef.value?.forEach((ref) => ref.setSkipNextWatch());
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      db_list: string[];
      dst_cluster: number;
      ignore_db_list: string[];
      rename_infos: RenameInfo[];
      restore_backup_file: SqlserverBackupLogModel;
      restore_time?: string;
      src_cluster: number;
    }[];
    is_time_fixed: boolean;
  }>(TicketTypes.SQLSERVER_ROLLBACK_LOCAL);

  watch(
    () => formData.rollbackMethod,
    () => {
      tableKey.value = random();
      formData.tableData = [createTableRow()];
    },
  );

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field as keyof RowData]: _.cloneDeep(value),
      });
    });
  };

  const handleClusterBatchEdit = (list: SqlserverHaModel[]) => {
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
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        backupRecord: item.backupRecord || undefined,
        backupTime: item.backupTime || '',
        cluster: {
          master_domain: item.master_domain,
        },
        databases: item.databases ? item.databases.split(',') : [],
        databasesIgnore: item.databasesIgnore ? item.databasesIgnore.split(',') : [],
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      editableTableRef.value?.validate();
    }, 200);
  };

  const handleSubmit = () => {
    Promise.all([formRef.value!.validate(), editableTableRef.value!.validate()]).then(() =>
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            db_list: item.databases,
            dst_cluster: item.cluster.id,
            ignore_db_list: item.databasesIgnore,
            rename_infos: item.renameInfos,
            restore_backup_file: item.backupRecord!,
            restore_time:
              formData.rollbackMethod === 'TIME' && item.backupTime ? formatDateToUTC(item.backupTime) : undefined,
            src_cluster: item.cluster.id,
          })),
          is_time_fixed: formData.rollbackMethod === 'TIME',
        },
        ...formData.payload,
      }),
    );
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'SqlserverToolboxIndex',
      });
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
