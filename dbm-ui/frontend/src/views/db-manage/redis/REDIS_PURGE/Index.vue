<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <BkAlert
        class="mb-16"
        closable
        theme="info"
        :title="t('清档：将目标集群中的数据进行清空，支持清档前进行备份。')" />
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
            <BackupColumn
              v-model="rowData.backup"
              @batch-edit="handleBatchEdit">
            </BackupColumn>
            <ForceColumn
              v-model="rowData.force"
              @batch-edit="handleBatchEdit">
            </ForceColumn>
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

  import BackupColumn, { BackupType } from './components/BackupColumn.vue';
  import ForceColumn, { ForceType } from './components/ForceColumn.vue';

  interface IDataRow {
    backup: string;
    cluster: {
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    force: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    backup: values.backup || BackupType.YES,
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    force: values.force || ForceType.NO,
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
    type: TicketTypes.REDIS_PURGE,
  });

  const { t } = useI18n();
  const route = useRoute();

  const tableKey = ref(random());

  useTicketDetail<Redis.Purge>(TicketTypes.REDIS_PURGE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.rules.map((item) =>
          createRowData({
            backup: item.backup ? BackupType.YES : BackupType.NO,
            cluster: {
              master_domain: item.domain,
            } as IDataRow['cluster'],
            force: item.force ? ForceType.YES : ForceType.NO,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    rules: {
      backup: boolean;
      cluster_id: number;
      cluster_type: string;
      db_list: [];
      domain: string;
      flushall: true; // TODO: 目前都是 true, 后续根据后端实现调整
      force: boolean;
    }[];
  }>(TicketTypes.REDIS_PURGE);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

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
      label: t('目标集群'),
    },
    {
      case: t('是'),
      key: 'backup',
      label: t('备份'),
      values: [t('是'), t('否')],
    },
    {
      case: t('否'),
      key: 'force',
      label: t('强制'),
      values: [t('是'), t('否')],
    },
  ];

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        backup: item.backup || '',
        cluster: {
          master_domain: item.domain || '',
        } as IDataRow['cluster'],
        force: item.force || '',
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
            backup: item.backup == BackupType.YES,
            cluster_id: item.cluster.id,
            cluster_type: item.cluster.cluster_type,
            db_list: [],
            domain: item.cluster.master_domain,
            flushall: true, // TODO: 目前都是 true, 后续根据后端实现调整
            force: item.force == ForceType.YES,
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
