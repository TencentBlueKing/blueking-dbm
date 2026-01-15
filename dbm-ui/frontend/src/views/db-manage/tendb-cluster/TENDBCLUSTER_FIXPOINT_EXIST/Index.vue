<template>
  <FixpointWrapper>
    <SmartAction>
      <BkFormItem
        :label="t('构造方式')"
        required>
        <CardCheckbox
          v-model="formData.rollbackMethod"
          :desc="t('使用备份文件构造数据')"
          icon="bk-dbm-icon db-icon-form"
          :title="t('指定备份记录构造数据')"
          true-value="BACKUPID" />
        <CardCheckbox
          v-model="formData.rollbackMethod"
          class="ml-8"
          :desc="t('使用指定的时间最近的 全备+binlog 构造数据')"
          icon="bk-dbm-icon db-icon-time"
          :title="t('指定时间构造数据')"
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
            :label="t('源集群')"
            :selected="selected"
            @batch-edit="handleClusterBatchEdit" />
          <BackupRecordColumn
            v-if="formData.rollbackMethod === 'BACKUPID'"
            v-model="item.backupRecord"
            v-model:table-data="formData.tableData"
            :backup-source="formData.backupSource"
            :cluster="item.cluster"
            @change="() => handleChangeRowData(item)" />
          <TimeBackupRecordColumn
            v-if="formData.rollbackMethod === 'TIME'"
            v-model:backup-record="item.backupRecord"
            v-model:backup-time="item.backupTime"
            v-model:table-data="formData.tableData"
            :backup-source="formData.backupSource"
            :cluster="item.cluster"
            @batch-edit="handleBatchEdit"
            @change="() => handleChangeRowData(item)" />
          <DbNameColumn
            v-model="item.databases"
            :cluster-id="item.cluster?.id"
            :readonly="diabledEdit(item)"
            field="databases"
            :label="t('源 DB')"
            required
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.tables"
            :cluster-id="item.cluster?.id"
            :readonly="diabledEdit(item)"
            field="tables"
            :label="t('源表')"
            required
            @batch-edit="handleBatchEdit" />
          <TargetClusterColumn
            v-model="item.targetCluster"
            :cluster="item.cluster"
            :selected="selectedTargetClusters" />
          <ConflictDbColumn
            v-model="item.affectDb"
            :readonly="diabledEdit(item)"
            :row-data="item" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
      <template #action>
        <BkButton
          class="mr-8 w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="ml-8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </FixpointWrapper>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import BackupLogRecordModel from '@services/model/tendbcluster/backup-log-record';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import BackupRecordColumn from './components/backup-record-column/Index.vue';
  import ConflictDbColumn from './components/conflict-db-column/Index.vue';
  import FixpointWrapper from './components/FixpointWrapper.vue';
  import TargetClusterColumn from './components/target-cluster-column/Index.vue';
  import TimeBackupRecordColumn from './components/time-backup-record-column/Index.vue';

  interface RowData {
    affectDb: string[];
    backupRecord: ComponentProps<typeof BackupRecordColumn>['modelValue'];
    backupTime: string;
    cluster: TendbClusterModel;
    databases: string[];
    tables: string[];
    targetCluster: TendbClusterModel;
  }

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const batchInputConfig = computed(() => {
    const base = [
      {
        case: 'tendbcluster.test.dba.db',
        key: 'master_domain',
        label: t('目标集群'),
      },
      {
        case: 'NULL',
        key: 'backupRecord',
        label: t('备份记录'),
      },
      {
        case: 'db1',
        key: 'databases',
        label: t('源 DB'),
      },
      {
        case: 'table1',
        key: 'tables',
        label: t('源表'),
      },
      {
        case: 'tendbha.test2.dba.db',
        key: 'targetCluster',
        label: t('目标集群'),
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
    affectDb: (data.affectDb || []) as string[],
    backupRecord: Object.assign({} as RowData['backupRecord'], data.backupRecord),
    backupTime: data.backupTime || '',
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
      } as TendbClusterModel,
      data.cluster,
    ),
    databases: (data.databases || []) as string[],
    tables: (data.tables || []) as string[],
    targetCluster: Object.assign(
      {
        id: 0,
        master_domain: '',
      } as TendbClusterModel,
      data.targetCluster,
    ),
  });

  const editableTableRef = useTemplateRef('editableTableRef');

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    payload: createTickePayload(),
    rollbackMethod: 'BACKUPID',
    tableData: [createTableRow()],
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());
  let isTicketLoaded = false;

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));
  const selectedTargetClusters = computed(() =>
    formData.tableData.filter((item) => item.targetCluster.id).map((item) => item.targetCluster),
  );

  useTicketDetail<TendbCluster.ResourcePool.RollbackCluster>(TicketTypes.TENDBCLUSTER_FIXPOINT_EXIST, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      isTicketLoaded = true;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        rollbackMethod: infos[0].rollback_time ? 'TIME' : 'BACKUPID',
      });
      nextTick(() => {
        formData.tableData = infos.map((item) =>
          createTableRow({
            backupRecord: item.backupinfo,
            backupTime: item.rollback_time,
            cluster: {
              master_domain: clusters[item.cluster_id]?.immute_domain || '',
            },
            databases: item.databases,
            tables: item.tables,
            targetCluster: {
              master_domain: clusters[item.target_cluster_id]?.immute_domain || '',
            },
          }),
        );
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      affect_database_list?: string[]; // 如果是回档到原集群 or 已有集群，需要填此参数
      backup_id: string;
      backup_source: BackupSourceType;
      backupinfo: BackupLogRecordModel; // 如果备份类型为REMOTE_AND_BACKUPID提供集群备份信息
      cluster_id: number;
      database_list: BackupLogRecordModel['database_list'];
      databases: string[];
      databases_ignore: string[];
      // 回档到新主机，指定机器需要填这个
      resource_spec?: {
        rollback_host: {
          count: number;
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: number;
        };
      };
      rollback_time?: string;
      rollback_type: string;
      tables: string[];
      tables_ignore: string[];
      target_cluster_id?: number; // 如果是回档到原集群 or 已有集群，需要填此参数
    }[];
    ip_source?: 'resource_pool'; // 只有在回档新集群选项，才传递此参数
    rollback_cluster_type: string;
  }>(TicketTypes.TENDBCLUSTER_FIXPOINT_EXIST);

  // 切换构造类型/方式、备份源时重置表格
  watch(
    () => formData.rollbackMethod,
    () => {
      tableKey.value = random();
      formData.tableData = [createTableRow()];
    },
  );

  const diabledEdit = (row: RowData) => {
    // 只要备份方式选择的是物理备份，则库，表字段默认填充*，且不可编辑
    if (row.backupRecord?.backup_type === 'physical') {
      return true;
    }
    // 指定时间构造数据，库，表字段默认填充*，且不可编辑
    if (formData.rollbackMethod === 'TIME') {
      return true;
    }
    return false;
  };

  const handleChangeRowData = (row: RowData) => {
    if (isTicketLoaded) {
      isTicketLoaded = false;
      return;
    }
    // 备份方式选择的是物理备份，则库，表字段默认填充*，且不可编辑
    // 逻辑备份时，源 DB，源表 默认改成空，需要且需要必填
    // 指定时间构造数据，库，表字段默认填充*，且不可编辑
    if (formData.rollbackMethod === 'TIME') {
      Object.assign(row, {
        databases: ['*'],
        tables: ['*'],
      });
    } else if (row.backupRecord?.backup_type === 'physical') {
      Object.assign(row, {
        databases: ['*'],
        tables: ['*'],
      });
    } else if (row.backupRecord?.backup_type === 'logical') {
      Object.assign(row, {
        databases: [],
        tables: [],
      });
    }
  };

  const handleClusterBatchEdit = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    for (const row of formData.tableData) {
      // 只读行不可通过表头修改
      if (['databases', 'tables'].includes(field) && row && diabledEdit(row)) {
        continue;
      }
      Object.assign(row, {
        [field as keyof RowData]: _.cloneDeep(value),
      });
    }
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        backupRecord: item.backupRecord || ({} as RowData['backupRecord']),
        backupTime: item.backupTime || '',
        cluster: {
          master_domain: item.master_domain,
        } as TendbClusterModel,
        databases: item.databases ? item.databases.split(',') : [],
        tables: item.tables ? item.tables.split(',') : [],
        targetCluster: {
          master_domain: item.targetCluster || '',
        } as TendbClusterModel,
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
    editableTableRef.value!.validate().then(() =>
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            affect_database_list: item.affectDb,
            backup_id: item.backupRecord.backup_id,
            backup_source: formData.backupSource,
            backupinfo: item.backupRecord,
            cluster_id: item.cluster.id,
            database_list: item.backupRecord.database_list,
            databases: item.databases,
            databases_ignore: [],
            // 指定时间构造需要传
            rollback_time:
              formData.rollbackMethod === 'TIME' && item.backupTime ? formatDateToUTC(item.backupTime) : undefined,
            rollback_type: `${formData.backupSource.toLocaleUpperCase()}_AND_${formData.rollbackMethod}`,
            tables: item.tables,
            tables_ignore: [],
            target_cluster_id: item.targetCluster.id,
          })),
          rollback_cluster_type: 'BUILD_INTO_EXIST_CLUSTER',
        },
        ...formData.payload,
      }),
    );
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
