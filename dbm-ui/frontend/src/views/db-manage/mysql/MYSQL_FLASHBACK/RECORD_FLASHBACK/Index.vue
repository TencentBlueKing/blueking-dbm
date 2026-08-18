<template>
  <SmartAction>
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
          :cluster-types="[ClusterTypes.TENDBHA]"
          :selected="selected"
          @batch-edit="handleClusterBatchEdit" />
        <DatetimeColumn
          v-model="item.start_time"
          :disabled-date="disableDate"
          field="start_time"
          :label="t('回档时间')"
          @batch-edit="handleBatchEdit"
          @change="() => handleDateChange(item)" />
        <DbNameColumn
          v-model="item.databases"
          :allow-asterisk="false"
          :cluster-id="item.cluster?.id"
          field="databases"
          :label="t('目标 DB')"
          required
          @batch-edit="handleBatchEdit" />
        <TableNameColumn
          v-model="item.tables"
          :allow-asterisk="false"
          :cluster-id="item.cluster?.id"
          field="tables"
          :label="t('目标表')"
          required
          @batch-edit="handleBatchEdit" />
        <RecordColumn
          v-model="item.rows_filter"
          :cluster-id="item.cluster?.id"
          @batch-edit="handleBatchEdit" />
        <OperationColumn
          v-model:table-data="formData.tableData"
          :create-row-method="createTableRow" />
      </EditableRow>
    </EditableTable>
    <BkFormItem
      class="mb-8"
      :label="t('日志追溯截止')"
      required>
      <BkRadioGroup v-model="formData.end_time_mode.mode">
        <BkRadio label="ticket_execute_time">
          {{ t('单据执行时间') }}
        </BkRadio>
        <BkRadio label="specified_time">
          {{ t('指定时间') }}
          <BkDatePicker
            v-if="formData.end_time_mode.mode === 'specified_time'"
            v-model="formData.end_time_mode.time"
            class="ml-16"
            :disabled-date="disableDate"
            :placeholder="t('请选择指定时间')"
            style="width: 240px"
            type="datetime" />
        </BkRadio>
      </BkRadioGroup>
    </BkFormItem>
    <BkFormItem class="mb-8">
      <BkCheckbox
        v-model="formData.direct_write_back"
        :false-label="false"
        true-label>
        {{ t('覆盖原始数据') }}
      </BkCheckbox>
    </BkFormItem>
    <BkFormItem>
      <BkCheckbox
        v-model="formData.conv_rows_update_to_write"
        :false-label="false"
        true-label>
        {{ t('update 转 replace') }}
      </BkCheckbox>
    </BkFormItem>
    <TicketPayload v-model="formData.payload" />
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
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { type Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';

  import { random } from '@utils';

  import DatetimeColumn from '../components/DatetimeColumn.vue';
  import RecordColumn from '../components/RecordColumn.vue';

  interface RowData {
    cluster: TendbhaModel;
    databases: string[];
    rows_filter: string;
    start_time: string;
    tables: string[];
  }

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();
  const router = useRouter();

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '2025-08-24T23:59:59',
      key: 'start_time',
      label: t('回档时间'),
    },
    {
      case: 'db1',
      key: 'databases',
      label: t('目标 DB'),
    },
    {
      case: 'table1',
      key: 'tables',
      label: t('目标库'),
    },
    {
      case: 'id,name\\n100,zhangsan',
      key: 'rows_filter',
      label: t('待闪回的记录'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
      } as TendbhaModel,
      data.cluster,
    ),
    databases: (data.databases || []) as string[],
    rows_filter: data.rows_filter || '',
    start_time: data.start_time || '',
    tables: (data.tables || []) as string[],
  });

  const editableTableRef = useTemplateRef('editableTableRef');

  const defaultData = () => ({
    conv_rows_update_to_write: false,
    direct_write_back: true,
    end_time_mode: {
      mode: 'ticket_execute_time',
      time: '',
    },
    flashback_type: 'RECORD_FLASHBACK',
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<Mysql.FlashBack>(TicketTypes.MYSQL_FLASHBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      formData.flashback_type = details.flashback_type;
      formData.payload.remark = ticketDetail.remark;
      formData.direct_write_back = details.infos[0].direct_write_back;
      formData.conv_rows_update_to_write = details.infos[0].conv_rows_update_to_write;
      formData.end_time_mode = details.infos[0].end_time
        ? {
            mode: 'specified_time',
            time: dayjs(details.infos[0].end_time).format('YYYY-MM-DD HH:mm:ss'),
          }
        : {
            mode: 'ticket_execute_time',
            time: '',
          };
      formData.tableData = details.infos.map((item) =>
        createTableRow({
          ...item,
          cluster: {
            id: item.cluster_id,
            master_domain: details.clusters[item.cluster_id].immute_domain,
          },
        }),
      );
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    flashback_type: 'RECORD_FLASHBACK';
    force: boolean;
    infos: {
      cluster_id: number;
      conv_rows_update_to_write: boolean;
      databases: string[];
      databases_ignore: string[];
      direct_write_back: boolean;
      end_time: string;
      rows_filter: string;
      start_time: string;
      tables: string[];
      tables_ignore: string[];
    }[];
  }>(TicketTypes.MYSQL_FLASHBACK);

  const disableDate = (date?: number | Date) => dayjs(date).isAfter(dayjs(), 'day');

  const handleDateChange = (row: RowData) => {
    if (row.start_time) {
      Object.assign(row, {
        end_time: 'now',
      });
    }
  };

  const handleClusterBatchEdit = (list: TendbhaModel[]) => {
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

  const handleBatchEdit = (value: string | string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        cluster: {
          master_domain: item.master_domain,
        } as TendbhaModel,
        databases: item.databases ? item.databases.split(',') : [],
        rows_filter: item.rows_filter?.replaceAll('\\n', '\n') || '',
        start_time: item.start_time || '',
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };

  const handleSubmit = () => {
    editableTableRef.value!.validate().then(() =>
      createTicketRun({
        details: {
          flashback_type: 'RECORD_FLASHBACK',
          force: true,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster?.id as number,
            conv_rows_update_to_write: formData.conv_rows_update_to_write,
            databases: item.databases,
            databases_ignore: [],
            direct_write_back: formData.direct_write_back,
            end_time:
              formData.end_time_mode.mode === 'ticket_execute_time' ? '' : formatDateToUTC(formData.end_time_mode.time),
            rows_filter: item.rows_filter,
            start_time: formatDateToUTC(item.start_time),
            tables: item.tables,
            tables_ignore: [],
          })),
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
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
