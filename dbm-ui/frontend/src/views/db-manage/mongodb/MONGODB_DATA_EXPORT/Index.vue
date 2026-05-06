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
    <div class="mongo-data-export-page db-toolbox">
      <BkAlert
        class="mb-16"
        theme="info"
        :title="t('数据导出：导出指定的数据，支持Json和Bson格式')" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              field="cluster.cluster_type_name"
              :label="t('集群类型')"
              readonly
              :width="130">
              <EditableBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')" />
            </EditableColumn>
            <DbNameColumn
              v-model="item.db_patterns"
              :cluster-id="item.cluster.id"
              field="db_patterns"
              :label="t('DB 名')"
              @batch-edit="handleDbTableBatchEdit" />
            <DbNameColumn
              v-model="item.ignore_dbs"
              :cluster-id="item.cluster.id"
              field="ignore_dbs"
              :label="t('忽略DB名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <TableNameColumn
              v-model="item.table_patterns"
              field="table_patterns"
              :label="t('表名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <TableNameColumn
              v-model="item.ignore_tables"
              field="ignore_tables"
              :label="t('忽略表名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <EditableColumn
              field="query"
              :label="t('查询条件')"
              :min-width="380"
              :required="false"
              :rules="queryRules">
              <EditableTextarea
                v-model="item.query"
                :placeholder="t('请输入合法的 JSON')" />
            </EditableColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <BkFormItem
          :label="t('导出格式')"
          property="format"
          required>
          <BkRadioGroup
            v-model="formData.format"
            size="small">
            <BkRadio label="json"> JSON </BkRadio>
            <BkRadio label="bson"> BSON </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
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
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mongodb/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mongodb/common/toolbox-field/table-name-column/Index.vue';

  import { isValidJSON, random } from '@utils';

  interface IDataRow {
    cluster: {
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    query: string;
    table_patterns: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    db_patterns: values.db_patterns || [],
    ignore_dbs: values.ignore_dbs || [],
    ignore_tables: values.ignore_tables || [],
    query: values.query || '',
    table_patterns: values.table_patterns || [],
  });

  const createDefaultFormData = () => ({
    format: 'json' as 'json' | 'bson',
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
    {
      case: 'db1,db2',
      key: 'db_patterns',
      label: t('DB 名'),
    },
    {
      case: 'db1,db2',
      key: 'ignore_dbs',
      label: t('忽略DB名'),
    },
    {
      case: 'table1,table2',
      key: 'table_patterns',
      label: t('表名'),
    },
    {
      case: 'table1,table2',
      key: 'ignore_tables',
      label: t('忽略表名'),
    },
    {
      case: '{"price":{"$gt":1}}',
      key: 'query',
      label: t('查询条件'),
    },
  ];

  const queryRules = [
    {
      message: '',
      trigger: 'change',
      validator: (value: string) => {
        if (value) {
          return isValidJSON(value) || t('请输入合法的 JSON');
        }
        return true;
      },
    },
  ];

  useTicketDetail<Mongodb.DataExport>(TicketTypes.MONGODB_DATA_EXPORT, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        format: infos[0]?.export_options?.format || 'json',
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createRowData({
            cluster: {
              master_domain: clusters[item.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            db_patterns: item.ns_filter.db_patterns,
            ignore_dbs: item.ns_filter.ignore_dbs,
            ignore_tables: item.ns_filter.ignore_tables,
            query: item.export_options.query || '',
            table_patterns: item.ns_filter.table_patterns,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Mongodb.DataExport['infos'];
  }>(TicketTypes.MONGODB_DATA_EXPORT);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => ({
            cluster_id: tableRow.cluster.id,
            export_options: {
              format: formData.format,
              query: tableRow.query || '',
            },
            ns_filter: {
              db_patterns: tableRow.db_patterns,
              ignore_dbs: tableRow.ignore_dbs,
              ignore_tables: tableRow.ignore_tables,
              table_patterns: tableRow.table_patterns,
            },
          })),
        },
        ...formData.payload,
      });
    }
  };

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
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

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
        db_patterns: item.db_patterns ? item.db_patterns.split(',') : [],
        ignore_dbs: item.ignore_dbs ? item.ignore_dbs.split(',') : [],
        ignore_tables: item.ignore_tables ? item.ignore_tables.split(',') : [],
        query: item.query || '',
        table_patterns: item.table_patterns ? item.table_patterns.split(',') : [],
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };

  const handleDbTableBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>

<style lang="less" scoped>
  .mongo-data-export-page {
    padding-bottom: 20px;
  }
</style>
