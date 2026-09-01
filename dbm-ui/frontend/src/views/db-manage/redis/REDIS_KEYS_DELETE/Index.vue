<template>
  <div class="sqlserver-db-backup-page">
    <SmartAction>
      <KeyOperationAlert />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <BkFormItem label="">
          <BkRadioGroup
            v-model="formData.type"
            @change="handleTypeChange">
            <BkRadioButton
              :key="TicketTypes.REDIS_KEYS_EXTRACT"
              :label="TicketTypes.REDIS_KEYS_EXTRACT"
              style="width: 160px">
              {{ t('提取 Key') }}
            </BkRadioButton>
            <BkRadioButton
              :key="TicketTypes.REDIS_KEYS_DELETE"
              :label="TicketTypes.REDIS_KEYS_DELETE"
              style="width: 160px">
              {{ t('删除 Key') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
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
              :width="150">
              <EditableBlock
                v-model="rowData.cluster.cluster_type_name"
                :placeholder="t('自动生成')">
              </EditableBlock>
            </EditableColumn>
            <KeyOperationColumn
              v-model="rowData.white_regex"
              field="white_regex"
              :label="t('包含 Key')"
              required
              @batch-edit="handleBatchEdit">
            </KeyOperationColumn>
            <KeyOperationColumn
              v-model="rowData.black_regex"
              field="black_regex"
              :label="t('排除 Key')"
              @batch-edit="handleBatchEdit">
            </KeyOperationColumn>
            <DeleteRateColumn
              v-model="rowData.delete_rate"
              :cluster-id="rowData.cluster.id" />
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
  import KeyOperationAlert from '@views/db-manage/redis/common/toolbox-common/key-operation-alert/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import KeyOperationColumn from '@views/db-manage/redis/common/toolbox-field/key-operation-column/Index.vue';

  import { random } from '@utils';

  import DeleteRateColumn from './components/DeleteRateColumn.vue';

  interface IDataRow {
    black_regex: string;
    cluster: {
      bk_cloud_id: number;
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    delete_rate: number | string;
    white_regex: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    black_regex: values.black_regex || '',
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    delete_rate: values.delete_rate || '',
    white_regex: values.white_regex || '',
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
    type: TicketTypes.REDIS_KEYS_DELETE,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  useTicketDetail<Redis.KeysDelete>(TicketTypes.REDIS_KEYS_DELETE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.rules.map((item) =>
          createRowData({
            black_regex: item.black_regex,
            cluster: {
              master_domain: item.domain,
            } as IDataRow['cluster'],
            // delete_rate: item.delete_rate,
            white_regex: item.white_regex,
          }),
        ),
      });

      nextTick(() => {
        formData.tableData.forEach((item, index) =>
          Object.assign(item, { delete_rate: details.rules[index]!.delete_rate }),
        );
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    delete_type: 'regex';
    rules: {
      black_regex: string;
      cluster_id: number;
      delete_rate: number;
      domain: string;
      white_regex: string;
    }[];
  }>(TicketTypes.REDIS_KEYS_DELETE);

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
        {
          handler: (data: RedisModel) => data.bk_cloud_id > 0,
          tip: t('暂不支持跨管控区域删除Key'),
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
      case: 'key1\\nkey2',
      key: 'white_regex',
      label: t('包含 Key'),
    },
    {
      case: 'key1\\nkey2',
      key: 'black_regex',
      label: t('排除 Key'),
    },
    {
      case: '5000',
      key: 'delete_rate',
      label: t('每秒删除 Key 个数'),
    },
  ];

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        black_regex: item.black_regex?.replaceAll('\\n', '\n') || '',
        cluster: {
          master_domain: item.domain || '',
        } as IDataRow['cluster'],
        delete_rate: item?.delete_rate ? Number(item.delete_rate) : '',
        white_regex: item.white_regex?.replaceAll('\\n', '\n') || '',
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
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
  };

  const handleBatchEdit = (value: string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    editableTableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          delete_type: 'regex',
          rules: formData.tableData.map((item) => ({
            black_regex: item.black_regex,
            cluster_id: item.cluster.id,
            delete_rate: Number(item.delete_rate),
            domain: item.cluster.master_domain,
            white_regex: item.white_regex,
          })),
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };

  const handleTypeChange = () => {
    router.replace({ name: TicketTypes.REDIS_KEYS_EXTRACT });
  };
</script>
