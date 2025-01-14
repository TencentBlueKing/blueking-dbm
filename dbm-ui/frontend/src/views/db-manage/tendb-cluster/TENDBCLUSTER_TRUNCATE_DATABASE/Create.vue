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
      :title="
        t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')
      " />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
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
          <TruncateTypeColumn
            v-model="item.truncateType"
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.dbPatterns"
            check-exist
            :cluster-id="item.cluster.id"
            field="dbPatterns"
            :label="t('目标DB名')"
            required
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.ignoreDbs"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="ignoreDbs"
            :label="t('忽略DB名')"
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.tablePatterns"
            check-exist
            :cluster-id="item.cluster.id"
            field="tablePatterns"
            :label="t('目标表名')"
            required
            @batch-edit="handleBatchEdit" />
          <TagDbNameColumn
            v-model="item.ignoreTables"
            check-not-exist
            :cluster-id="item.cluster.id"
            field="ignoreTables"
            :label="t('忽略表名')"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <BkFormItem class="ignore-biz">
        <BkCheckbox
          v-model="formData.isSafe"
          :false-label="false"
          true-label>
          <span
            v-bk-tooltips="t('安全模式下_存在业务连接时需要人工确认')"
            class="safe-action-text">
            {{ t('安全模式') }}
          </span>
        </BkCheckbox>
      </BkFormItem>
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TagDbNameColumn from '@views/db-manage/common/toolbox-field/column/tag-db-name-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import TruncateTypeColumn from './components/TruncateTypeColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
    };
    truncateType: string;
    dbPatterns: string[];
    ignoreDbs: string[];
    tablePatterns: string[];
    ignoreTables: string[];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
    },
    truncateType: data.truncateType || '',
    dbPatterns: data.dbPatterns || [],
    ignoreDbs: data.ignoreDbs || [],
    tablePatterns: data.tablePatterns || [],
    ignoreTables: data.ignoreTables || [],
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    isSafe: false,
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      cluster_id: number;
      truncate_data_type: string;
      db_patterns: string[];
      table_patterns: string[];
      ignore_dbs: string[];
      ignore_tables: string[];
    }[];
  }>(TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          truncate_data_type: item.truncateType,
          db_patterns: item.dbPatterns,
          table_patterns: item.tablePatterns,
          ignore_dbs: item.ignoreDbs,
          ignore_tables: item.ignoreTables,
        })),
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

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      item[field as keyof RowData] = value;
    });
  };
</script>

<style lang="less" scoped>
  .safe-action-text {
    padding-bottom: 2px;
    border-bottom: 1px dashed #979ba5;
  }
</style>
