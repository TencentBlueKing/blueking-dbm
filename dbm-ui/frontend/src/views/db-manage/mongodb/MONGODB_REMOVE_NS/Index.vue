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
    <div class="mongo-db-clear-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')
        " />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
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
              :width="150">
              <EditableBlock
                v-model="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')" />
            </EditableColumn>
            <DropTypeColumn
              v-model="item.drop_type"
              @batch-edit="handleBatchEdit" />
            <DropIndexColumn
              v-model="item.drop_index"
              @batch-edit="handleBatchEdit" />
            <DbNameColumn
              v-model="item.db_patterns"
              :cluster-id="item.cluster.id"
              field="db_patterns"
              :label="t('备份DB名')"
              @batch-edit="handleBatchEdit" />
            <DbNameColumn
              v-model="item.ignore_dbs"
              :cluster-id="item.cluster.id"
              :compare-data="item.ignore_tables"
              field="ignore_dbs"
              :label="t('忽略 DB 名')"
              :required="false"
              @batch-edit="handleBatchEdit" />
            <TableNameColumn
              v-model="item.table_patterns"
              field="table_patterns"
              :label="t('备份表名')"
              @batch-edit="handleBatchEdit" />
            <TableNameColumn
              v-model="item.ignore_tables"
              :compare-data="item.ignore_dbs"
              field="ignore_tables"
              :label="t('忽略表名')"
              :required="false"
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <IgnoreBiz
          v-model="formData.ignore_business_access"
          v-bk-tooltips="t('如忽略_有连接的情况下也会执行')" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mongodb/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mongodb/common/toolbox-field/table-name-column/Index.vue';

  import DropIndexColumn, { DropIndex } from './components/DropIndexColumn.vue';
  import DropTypeColumn from './components/DropTypeColumn.vue';

  export interface IDataRow {
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    db_patterns: string[];
    drop_index: string;
    drop_type: string;
    ignore_dbs: string[];
    ignore_tables: string[];
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
    drop_index: values.drop_index || '',
    drop_type: values.drop_type || '',
    ignore_dbs: values.ignore_dbs || [],
    ignore_tables: values.ignore_tables || [],
    table_patterns: values.table_patterns || [],
  });

  const createDefaultFormData = () => ({
    ignore_business_access: false,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.RemoveNs>(TicketTypes.MONGODB_REMOVE_NS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos, is_safe: isSafe } = details;
      Object.assign(formData, {
        ignore_business_access: !isSafe,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createRowData({
            cluster: {
              master_domain: clusters[item.cluster_ids[0]].immute_domain,
            } as IDataRow['cluster'],
            db_patterns: item.ns_filter.db_patterns,
            drop_index: item.drop_index ? DropIndex.DELETE : DropIndex.KEEP,
            drop_type: item.drop_type,
            ignore_dbs: item.ns_filter.ignore_dbs,
            ignore_tables: item.ns_filter.ignore_tables,
            table_patterns: item.ns_filter.table_patterns,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      drop_index: boolean;
      drop_type: string;
      ns_filter: {
        db_patterns: string[];
        ignore_dbs: string[];
        ignore_tables: string[];
        table_patterns: string[];
      };
    }[];
    is_safe: boolean;
  }>(TicketTypes.MONGODB_REMOVE_NS);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

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
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: string[] | string, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => ({
            cluster_ids: [tableRow.cluster.id],
            cluster_type: tableRow.cluster.cluster_type,
            drop_index: tableRow.drop_index !== DropIndex.KEEP,
            drop_type: tableRow.drop_type,
            ns_filter: {
              db_patterns: tableRow.db_patterns,
              ignore_dbs: tableRow.ignore_dbs,
              ignore_tables: tableRow.ignore_tables,
              table_patterns: tableRow.table_patterns,
            },
          })),
          is_safe: !formData.ignore_business_access,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mongo-db-clear-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 20px;

      .safe-action-text {
        padding-bottom: 2px;
        border-bottom: 1px dashed #979ba5;
      }
    }
  }
</style>
