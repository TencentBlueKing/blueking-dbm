<template>
  <div class="tendbcluster-toolbox-record-flashback-page">
    <SmartAction>
      <BkAlert
        class="mb-10"
        closable
        theme="info"
        :title="t('闪回：通过 flashback 工具，对 row 格式的 binlog 做逆向操作')" />
      <BkForm
        ref="formRef"
        class="mb-24"
        form-type="vertical">
        <BkFormItem
          :label="t('时区')"
          required>
          <TimeZonePicker style="width: 450px" />
        </BkFormItem>
        <BkFormItem
          :label="t('闪回方式')"
          required>
          <BkRadioGroup
            v-model="formData.flashback_type"
            @change="handleFlashbackTypeChange">
            <BkRadioButton
              label="TABLE_FLASHBACK"
              style="width: 225px">
              {{ t('库表闪回') }}
            </BkRadioButton>
            <BkRadioButton
              label="RECORD_FLASHBACK"
              style="width: 225px">
              {{ t('记录级闪回') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <EditableTable
          ref="editableTableRef"
          :model="formData.tableData">
          <EditableTableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="rowData.cluster"
              :selected-ids="selectedClusterIds"
              @batch-edit="handleBatchEdit" />
            <DatetimeColumn
              v-model="rowData.start_time"
              :disabled-date="(date) => handleStartTimeDisableCallback(date, getDateNow())"
              field="start_time"
              :label="t('回档时间')"
              @change="() => handleDateChange(rowData)" />
            <DatetimeColumn
              v-model="rowData.end_time"
              :disabled-date="(date) => handleEditTimeDisableCallback(date, rowData.start_time)"
              field="end_time"
              :label="t('截止时间')"
              nowenable />
            <DbNameColumn
              v-model="rowData.databases"
              :cluster-id="rowData.cluster?.id" />
            <TableNameColumn
              v-model="rowData.tables"
              :cluster-id="rowData.cluster?.id"
              :label="t('目标表')" />
            <RecordColumn
              v-model="rowData.rows_filter"
              :cluster-id="rowData.cluster?.id" />
            <OperationColumn
              v-model:table-data="formData.tableData"
              :create-row-method="createTableData" />
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
      </BkForm>
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
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail, useTimeZoneFormat } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import DatetimeColumn from './components/DatetimeColumn.vue';
  import DbNameColumn from './components/DbNameColumn.vue';
  import OperationColumn from './components/OperationColumn.vue';
  import RecordColumn from './components/RecordColumn.vue';
  import TableNameColumn from './components/TableNameColumn.vue';

  interface IRowData {
    cluster?: {
      id?: number;
      master_domain?: string;
    };
    databases?: string[];
    direct_write_back?: boolean;
    end_time?: string;
    rows_filter?: string;
    start_time?: string;
    tables?: string[];
  }

  const { t } = useI18n();
  const router = useRouter();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const createTableData = (data = {} as IRowData) => ({
    cluster: data.cluster,
    databases: data.databases || [],
    direct_write_back: data.direct_write_back || false,
    end_time: data.end_time || '',
    rows_filter: data.rows_filter || '',
    start_time: data.start_time || '',
    tables: data.tables || [],
  });

  const formRef = useTemplateRef('formRef');
  const editableTableRef = useTemplateRef('editableTableRef');
  const defaultData = () => ({
    direct_write_back: true,
    flashback_type: 'RECORD_FLASHBACK',
    payload: createTickePayload(),
    tableData: [createTableData()],
  });
  const formData = reactive(defaultData());

  useTicketDetail<TendbCluster.FlashBack>(TicketTypes.TENDBCLUSTER_FLASHBACK, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      if (details.flashback_type === 'TABLE_FLASHBACK') {
        router.push({
          name: 'spiderFlashback',
        });
        return;
      }
      formData.flashback_type = details.flashback_type;
      formData.payload.remark = ticketDetail.remark;
      formData.direct_write_back = details.infos[0].direct_write_back;
      formData.tableData = details.infos.map((item) =>
        createTableData({
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

  const selectedClusterIds = computed(() =>
    _.filter(
      formData.tableData.map((item) => item.cluster?.id || 0),
      (item) => Number(item) > 0,
    ),
  );

  const handleFlashbackTypeChange = (type: string) => {
    if (type === 'TABLE_FLASHBACK') {
      router.push({
        name: 'spiderFlashback',
      });
    }
  };

  const getDateNow = () => dayjs(Date.now()).format('YYYY-MM-DD HH:mm:ss');

  const handleStartTimeDisableCallback = (date: Date | number, endDate: string) => dayjs(date).isAfter(dayjs(endDate));

  const handleEditTimeDisableCallback = (date: Date | number, startDate: string) =>
    dayjs(date).isBefore(dayjs(startDate));

  const handleDateChange = (row: IRowData) => {
    if (row.start_time) {
      Object.assign(row, {
        end_time: getDateNow(),
      });
    }
  };

  const handleBatchEdit = (list: TendbclusterModel[]) => {
    const dataList = list.reduce<ReturnType<typeof createTableData>[]>((acc, item) => {
      if (!selectedClusterIds.value.includes(item.id)) {
        acc.push(
          createTableData({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selectedClusterIds.value.length ? formData.tableData : []), ...dataList];
  };

  const handleSubmit = () => {
    Promise.all([formRef.value!.validate(), editableTableRef.value!.validate()]).then(() =>
      createTicketRun({
        details: {
          flashback_type: 'RECORD_FLASHBACK',
          force: true,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.cluster?.id as number,
            databases: item.databases,
            databases_ignore: [],
            direct_write_back: formData.direct_write_back,
            end_time: formatDateToUTC(item.end_time),
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
<style lang="less">
  .tendbcluster-toolbox-record-flashback-page {
    .bk-form-label {
      font-weight: bold;
      color: #313238;
    }
  }
</style>
