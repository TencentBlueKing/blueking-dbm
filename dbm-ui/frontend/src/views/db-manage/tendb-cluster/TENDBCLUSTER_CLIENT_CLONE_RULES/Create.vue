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
      :title="t('客户端权限克隆：访问 DB 来源 IP 替换时做的权限克隆')" />
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
          <ModuleColumn
            v-model="item.module"
            :source="item.source" />
          <Column
            field="source.bk_cloud_id"
            :label="t('所属管控区域')"
            :min-width="150"
            required>
            <Block v-if="item.source.bk_host_id">
              {{ cloudAreaMap[item.source.bk_cloud_id] }}
            </Block>
            <Block
              v-else
              :placeholder="t('自动生成')" />
          </Column>
          <Column
            field="target"
            :label="t('新客户端IP')"
            :min-width="150"
            required>
            <TagInput v-model="item.target" />
          </Column>
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

  import EditableTable, {
    Block,
    Column,
    Row as EditableTableRow,
    TagInput,
  } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import ModuleColumn from './components/ModuleColumn.vue';
  import SourceColumn, { type SelectorHost } from './components/SourceColumn.vue';

  interface RowData {
    source: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      bk_host_innerip: string;
    };
    module: string;
    target: string[];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    source: data.source || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      bk_host_innerip: '',
    },
    module: data.module || '',
    target: data.target || [],
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
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useRequest(getCloudList, {
    onSuccess(data) {
      Object.assign(cloudAreaMap, Object.fromEntries(data.map((cur) => [cur.bk_cloud_id, cur.bk_cloud_name])));
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<
    ServiceReturnType<typeof precheckPermissionClone> & {
      clone_type: 'client';
    }
  >(TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const precheckResult = await precheckPermissionClone({
      bizId: window.PROJECT_CONFIG.BIZ_ID,
      clone_type: 'client',
      clone_list: formData.tableData.map((item) => ({
        bk_cloud_id: item.source.bk_cloud_id,
        module: item.module,
        source: item.source.ip,
        target: item.target.join('\n'),
      })),
      clone_cluster_type: 'tendbcluster',
    });
    createTicketRun({
      details: {
        ...precheckResult,
        clone_type: 'client',
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            source: {
              bk_cloud_id: item.cloud_id,
              bk_host_id: item.host_id,
              ip: item.ip,
              bk_host_innerip: `${item.cloud_id}:${item.ip}`,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
