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
  <SmartAction>
    <BkAlert
      class="mb-20"
      closable
      :title="t('闪回：通过 flashback 工具，对 row 格式的 binlog 做逆向操作')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <div class="title-spot mt-12 mb-10">{{ t('时区') }}<span class="required" /></div>
      <TimeZonePicker style="width: 450px" />
      <EditableTable
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <StartTimeColumn v-model="item.startTime" />
          <EndTimeColumn
            v-model="item.endTime"
            :start-time="item.startTime" />
          <TagDbNameColumn
            v-model="item.databases"
            check-exist
            :cluster-id="item.cluster.id"
            field="databases"
            :label="t('目标库')"
            required />
          <TagDbNameColumn
            v-model="item.databasesIgnore"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="databasesIgnore"
            :label="t('忽略库')" />
          <TagDbNameColumn
            v-model="item.tables"
            check-exist
            :cluster-id="item.cluster.id"
            field="tables"
            :label="t('目标表')"
            required />
          <TagDbNameColumn
            v-model="item.tablesIgnore"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="tablesIgnore"
            :label="t('忽略表')" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <TicketRemark v-model="formData.remark" />
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
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { checkFlashbackDatabase } from '@services/source/remoteService';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';
  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TagDbNameColumn from '@views/db-manage/common/toolbox-field/column/tag-db-name-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import { messageError } from '@utils';

  import ClusterColumn from './components/ClusterColumn.vue';
  import EndTimeColumn from './components/EndTimeColumn.vue';
  import StartTimeColumn from './components/StartTimeColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
    };
    startTime: string;
    endTime: string;
    databases: string[];
    databasesIgnore: string[];
    tables: string[];
    tablesIgnore: string[];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
    },
    startTime: data.startTime || '',
    endTime: data.endTime || '',
    databases: data.databases || [],
    databasesIgnore: data.databasesIgnore || [],
    tables: data.tables || [],
    tablesIgnore: data.tablesIgnore || [],
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      cluster_id: number;
      start_time: string;
      end_time: string;
      databases: string[];
      tables: string[];
      databases_ignore: string[];
      tables_ignore: string[];
    }[];
  }>(TicketTypes.TENDBCLUSTER_FLASHBACK);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const infos = formData.tableData.map((item) => ({
      cluster_id: item.cluster.id,
      start_time: item.startTime,
      end_time: item.endTime,
      databases: item.databases,
      tables: item.tables,
      databases_ignore: item.databasesIgnore,
      tables_ignore: item.tablesIgnore,
    }));
    const checkResult = await checkFlashbackDatabase({
      infos,
    });
    const checkResultError = _.find(checkResult, (item) => !!item.message);
    if (checkResultError) {
      messageError(checkResultError.message);
      return;
    }
    createTicketRun({
      details: {
        infos,
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
