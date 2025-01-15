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
      :title="t('DB 实例权限克隆：DB 实例 IP 替换时，克隆原实例的所有权限到新实例中')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <SourceColumn
            v-model="item.source"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <Column
            field="source.cluster_id"
            :label="t('所属集群')"
            :min-width="150"
            required>
            <Block
              v-model="item.source.master_domain"
              :placeholder="t('自动生成')" />
          </Column>
          <Column
            field="source.db_module_id"
            :label="t('模块')"
            :min-width="150"
            required>
            <Block
              v-model="item.source.db_module_name"
              :placeholder="t('自动生成')" />
          </Column>
          <TargetColumn
            v-model="item.target"
            :source="item.source"
            :table-data="formData.tableData" />
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getCloudList } from '@services/source/ipchooser';
  import { precheckPermissionClone } from '@services/source/mysqlPermissionAuthorize';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import SourceColumn, { type SelectorHost } from './components/SourceColumn.vue';
  import TargetColumn from './components/TargetColumn.vue';

  interface RowData {
    source: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      instance_address: string;
      cluster_id: number;
      master_domain: string;
      db_module_id: number;
      db_module_name: string;
    };
    target: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    source: data.source || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      port: 0,
      instance_address: '',
      cluster_id: 0,
      master_domain: '',
      db_module_id: 0,
      db_module_name: '',
    },
    target: data.target || '',
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());
  const cloudAreaMap = reactive<Record<number, string>>({});

  const selected = computed(() =>
    formData.tableData.filter((item) => item.source.bk_host_id).map((item) => item.source),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  useRequest(getCloudList, {
    onSuccess(data) {
      Object.assign(cloudAreaMap, Object.fromEntries(data.map((cur) => [cur.bk_cloud_id, cur.bk_cloud_name])));
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<
    ServiceReturnType<typeof precheckPermissionClone> & {
      clone_type: 'instance';
    }
  >(TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const precheckResult = await precheckPermissionClone({
      bizId: window.PROJECT_CONFIG.BIZ_ID,
      clone_type: 'instance',
      clone_list: formData.tableData.map((item) => ({
        bk_cloud_id: item.source.bk_cloud_id,
        cluster_domain: item.source.master_domain,
        module: item.source.db_module_id,
        source: item.source.instance_address,
        target: item.target,
      })),
      clone_cluster_type: 'tendbcluster',
    });
    createTicketRun({
      details: {
        ...precheckResult,
        clone_type: 'instance',
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            source: {
              bk_host_id: item.bk_host_id,
              bk_cloud_id: item.bk_cloud_id,
              ip: item.ip,
              port: item.port,
              instance_address: item.instance_address,
              cluster_id: item.cluster_id,
              master_domain: item.master_domain,
              db_module_id: item.db_module_id,
              db_module_name: item.db_module_name,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
