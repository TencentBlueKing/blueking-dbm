<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('清档_删除目标数据库数据_数据会暂存在不可见的备份库中_只有在执行删除备份库后_才会真正的删除数据')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16 toolbox-form"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            allow-repeat
            only-one-type
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <TruncateTypeColumn
            v-model="item.truncate_data_type"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.db_patterns"
            :cluster-id="item.cluster?.id"
            field="db_patterns"
            :label="t('目标 DB 名')"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_dbs"
            :cluster-id="item.cluster?.id"
            field="ignore_dbs"
            :label="t('忽略 DB 名')"
            :required="false"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.table_patterns"
            :cluster-id="item.cluster?.id"
            field="table_patterns"
            :label="t('目标表名')"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.ignore_tables"
            :cluster-id="item.cluster?.id"
            field="ignore_tables"
            :label="t('忽略表名')"
            :required="false"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem>
        <BkCheckbox
          v-model="formData.force"
          :false-label="false"
          true-label>
          <span
            v-bk-tooltips="t('安全模式下_存在业务连接时需要人工确认')"
            class="safe-action-text">
            {{ t('安全模式') }}
          </span>
        </BkCheckbox>
      </BkFormItem>
      <BkFormItem
        :label="t('删除备份库时间')"
        required>
        <BkRadioGroup v-model="formData.clear_mode">
          <BkRadio :label="7">{{ t('7天后') }}</BkRadio>
          <BkRadio :label="15">{{ t('15天后') }}</BkRadio>
          <BkRadio label="manual">{{ t('手动') }}</BkRadio>
        </BkRadioGroup>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';
  import TicketModel from '@services/model/ticket/ticket';

  import { useCreateTicket } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/edit-table-column/DbNameColumn.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/edit-table-column/TableNameColumn.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import TruncateTypeColumn from './components/TruncateTypeColumn.vue';

  interface Exposes {
    cloneTicket(ticketDetail: TicketModel<Mysql.TruncateData>): void;
  }

  interface RowData {
    cluster: TendbhaModel;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
    truncate_data_type: string;
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'drop_table',
      key: 'truncate_data_type',
      label: t('清档类型'),
    },
    {
      case: '*',
      key: 'db_patterns',
      label: t('目标 DB 名'),
    },
    {
      case: 'NULL',
      key: 'ignore_dbs',
      label: t('忽略 DB 名'),
    },
    {
      case: '*',
      key: 'table_patterns',
      label: t('目标表名'),
    },
    {
      case: 'NULL',
      key: 'ignore_tables',
      label: t('忽略表名'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.cluster,
    ),
    db_patterns: data.db_patterns || ['*'],
    ignore_dbs: data.ignore_dbs || [],
    ignore_tables: data.ignore_tables || [],
    table_patterns: data.table_patterns || ['*'],
    truncate_data_type: data.truncate_data_type || '',
  });

  const defaultData = () => ({
    clear_mode: 7 as number | string,
    force: false,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  interface TicketDetails {
    clear_mode: {
      days?: number;
      mode: string;
    };
    infos: {
      cluster_id: number;
      db_patterns: string[];
      force: boolean;
      ignore_dbs: string[];
      ignore_tables: string[];
      table_patterns: string[];
      truncate_data_type: string;
    }[];
  }

  const { loading: isHaSubmitting, run: haCreateTicketRun } = useCreateTicket<TicketDetails>(
    TicketTypes.MYSQL_HA_TRUNCATE_DATA,
  );

  const { loading: isSingleSubmitting, run: singleCreateTicketRun } = useCreateTicket<TicketDetails>(
    TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA,
  );

  const isSubmitting = computed(() => isHaSubmitting.value || isSingleSubmitting.value);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const clearMode: TicketDetails['clear_mode'] = {
      mode: 'manual',
    };
    if (formData.clear_mode !== 'manual') {
      Object.assign(clearMode, {
        days: formData.clear_mode,
        mode: 'timer',
      });
    }
    let createTicketRun = haCreateTicketRun;
    if (formData.tableData[0].cluster.cluster_type === ClusterTypes.TENDBSINGLE) {
      createTicketRun = singleCreateTicketRun;
    }
    createTicketRun({
      details: {
        clear_mode: clearMode,
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          db_patterns: item.db_patterns,
          force: formData.force,
          ignore_dbs: item.ignore_dbs,
          ignore_tables: item.ignore_tables,
          table_patterns: item.table_patterns,
          truncate_data_type: item.truncate_data_type,
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            cluster,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
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
        db_patterns: item.db_patterns ? item.db_patterns.split(',') : [],
        ignore_dbs: item.ignore_dbs ? item.ignore_dbs.split(',') : [],
        ignore_tables: item.ignore_tables ? item.ignore_tables.split(',') : [],
        table_patterns: item.table_patterns ? item.table_patterns.split(',') : [],
        truncate_data_type: item.truncate_data_type || '',
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };

  defineExpose<Exposes>({
    cloneTicket(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        clear_mode: details.clear_mode?.days || details.clear_mode.mode,
        force: infos[0].force,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            cluster: {
              master_domain: clusters[item.cluster_id].immute_domain || '',
            } as TendbhaModel,
            db_patterns: item.db_patterns,
            ignore_dbs: item.ignore_dbs,
            ignore_tables: item.ignore_tables,
            table_patterns: item.table_patterns,
            truncate_data_type: item.truncate_data_type,
          }),
        ),
      });
    },
  });
</script>
