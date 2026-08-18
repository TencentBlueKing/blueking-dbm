<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <BkAlert
        class="mb-16"
        closable
        theme="info"
        :title="t('备份：针对集群进行数据备份')" />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <BatchInput
          :config="batchInputConfig"
          @change="handleBatchInput" />
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-24"
          :model="formData.tableData">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('架构版本')"
              readonly
              :width="300">
              <EditableBlock
                v-model="rowData.cluster.cluster_type_name"
                :placeholder="t('自动生成')">
              </EditableBlock>
            </EditableColumn>
            <TargetColumn
              v-model="rowData.target"
              @batch-edit="handleBatchEdit">
            </TargetColumn>
            <BackupTypeColumn
              v-model="rowData.backup_type"
              @batch-edit="handleBatchEdit">
            </BackupTypeColumn>
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

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import BackupTypeColumn, { BackupType } from './components/BackupTypeColumn.vue';
  import TargetColumn from './components/TargetColumn.vue';

  interface IDataRow {
    backup_type: string;
    cluster: {
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    target: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    backup_type: values.backup_type || BackupType.NORMAL_BACKUP,
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    target: values.target || 'slave',
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
    type: TicketTypes.REDIS_BACKUP,
  });

  const { t } = useI18n();
  const route = useRoute();

  useTicketDetail<Redis.Backup>(TicketTypes.REDIS_BACKUP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.rules.map((item) =>
          createRowData({
            backup_type: item.backup_type,
            cluster: {
              master_domain: item.domain,
            } as IDataRow['cluster'],
            target: item.target,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    rules: {
      backup_type: string;
      cluster_id: number;
      domain: string;
      target: string;
    }[];
  }>(TicketTypes.REDIS_BACKUP);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());
  const formData = reactive(createDefaultFormData());

  // 集群列表跳转
  const { masterDomain } = route.query as { masterDomain: string };
  if (masterDomain) {
    const domainList = masterDomain.split(',');
    Object.assign(formData, {
      tableData: domainList.map((domain) =>
        createRowData({
          cluster: {
            master_domain: domain,
          } as IDataRow['cluster'],
        }),
      ),
    });
  }

  const selected = computed(() =>
    formData.tableData.filter((item) => item.cluster.master_domain).map((item) => item.cluster),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      disabledRowConfig: [
        {
          handler: (data: RedisModel) =>
            data.operations.some((item) =>
              [TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_INSTANCE_DESTROY].includes(item.ticket_type as TicketTypes),
            ),
          tip: t('集群删除中无法选择'),
        },
      ],
    },
  } as unknown as Record<string, TabItem>;

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
      key: 'domain',
      label: t('集群域名'),
    },
    {
      case: 'Slave',
      key: 'target',
      label: t('备份目标'),
      values: ['Master', 'Slave'],
    },
    {
      case: t('1个月'),
      key: 'backup_type',
      label: t('备份类型'),
      values: [t('1个月'), t('3年')],
    },
  ];

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        backup_type: item.backup_type || BackupType.NORMAL_BACKUP,
        cluster: {
          cluster_type: '' as ClusterTypes,
          cluster_type_name: '',
          id: 0,
          master_domain: item.domain || '',
        },
        target: item.target || 'slave',
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...newList];
  };

  const handleBatchEdit = (value: string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          rules: formData.tableData.map((item) => ({
            backup_type: item.backup_type,
            cluster_id: item.cluster.id,
            domain: item.cluster.master_domain,
            target: item.target,
          })),
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>
