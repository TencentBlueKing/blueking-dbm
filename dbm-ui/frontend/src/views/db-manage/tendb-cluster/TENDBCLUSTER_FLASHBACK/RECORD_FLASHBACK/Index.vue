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
      <EditableTableRow
        v-for="(item, index) in formData.tableData"
        :key="index">
        <ClusterColumn
          v-model="item.cluster"
          :selected="selected"
          @batch-edit="handleClusterBatchEdit" />
        <DatetimeColumn
          v-model="item.start_time"
          :disabled-date="(date) => handleStartTimeDisableCallback(date, getDateNow())"
          field="start_time"
          :label="t('回档时间')"
          @batch-edit="handleBatchEdit"
          @change="() => handleDateChange(item)" />
        <DatetimeColumn
          v-model="item.end_time"
          :disabled-date="(date) => handleEditTimeDisableCallback(date, item.start_time)"
          field="end_time"
          :label="t('截止时间')"
          nowenable
          @batch-edit="handleBatchEdit" />
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
      </EditableTableRow>
    </EditableTable>
    <BkFormItem class="mt-20">
      <BkCheckbox
        v-model="formData.direct_write_back"
        :false-label="false"
        true-label>
        {{ t('覆盖原始数据') }}
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
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';
  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import { TicketTypes } from '@common/const';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import DbNameColumn from '@views/db-manage/tendb-cluster/common/edit-table-column/DbNameColumn.vue';
  import TableNameColumn from '@views/db-manage/tendb-cluster/common/edit-table-column/TableNameColumn.vue';

  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';
  import DatetimeColumn from '../components/DatetimeColumn.vue';
  import RecordColumn from '../components/RecordColumn.vue';
  import { random } from '@utils';

  interface RowData {
    cluster: TendbclusterModel;
    databases: string[];
    direct_write_back: boolean;
    end_time: string;
    rows_filter: string;
    start_time: string;
    tables: string[];
  }

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

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
      case: 'now',
      key: 'end_time',
      label: t('截止时间'),
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
      case: 'id,name/100,zhangsan (/ 表示换行)',
      key: 'rows_filter',
      label: t('待闪回的记录'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    direct_write_back: data.direct_write_back || false,
    rows_filter: data.rows_filter || '',
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
      } as TendbclusterModel,
      data.cluster,
    ),
    databases: (data.databases || []) as string[],
    tables: (data.tables || []) as string[],
    start_time: data.start_time || '',
    end_time: data.end_time || '',
  });

  const editableTableRef = useTemplateRef('editableTableRef');

  const defaultData = () => ({
    direct_write_back: true,
    flashback_type: 'RECORD_FLASHBACK',
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<TendbCluster.FlashBack>(TicketTypes.TENDBCLUSTER_FLASHBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      formData.flashback_type = details.flashback_type;
      formData.payload.remark = ticketDetail.remark;
      formData.direct_write_back = details.infos[0].direct_write_back;
      formData.tableData = details.infos.map((item) =>
        createTableRow({
          ...item,
          cluster: {
            master_domain: details.clusters[item.cluster_id].immute_domain || '',
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
      databases: string[];
      databases_ignore: string[];
      direct_write_back: boolean;
      end_time: string;
      rows_filter: string;
      start_time: string;
      tables: string[];
      tables_ignore: string[];
    }[];
  }>(TicketTypes.TENDBCLUSTER_FLASHBACK);

  const getDateNow = () => dayjs(Date.now()).format('YYYY-MM-DD HH:mm:ss');

  const handleStartTimeDisableCallback = (date: Date | number, endDate: string) =>
    dayjs(date).isAfter(dayjs(endDate), 'day');

  const handleEditTimeDisableCallback = (date: Date | number, startDate: string) =>
    dayjs(date).isBefore(dayjs(startDate));

  const handleDateChange = (row: RowData) => {
    if (row.start_time) {
      Object.assign(row, {
        end_time: 'now',
      });
    }
  };

  const handleClusterBatchEdit = (list: TendbclusterModel[]) => {
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
        } as TendbclusterModel,
        tables: item.tables ? [item.tables] : [],
        databases: item.databases ? [item.databases] : [],
        start_time: item.start_time || '',
        end_time: item.end_time || '',
        rows_filter: item.rows_filter?.replace('/', '\n') || '',
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
          flashback_type: 'RECORD_FLASHBACK',
          force: true,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster?.id as number,
            databases: item.databases,
            databases_ignore: [],
            direct_write_back: formData.direct_write_back,
            end_time: formatDateToUTC(item.end_time === 'now' ? '' : item.end_time),
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
</script>
