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
      :title="t('客户端权限克隆：访问 DB 来源 IP 替换时做的权限克隆')" />
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
          <SourceColumn
            v-model:bk-cloud-id="item.bk_cloud_id"
            v-model:module="item.module"
            v-model:source="item.source"
            @batch-edit="handleBatchEditNetIp" />
          <TargetColumn
            v-model="item.target"
            :source="item.source" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
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

  import type { TendbCluster } from '@services/model/ticket/ticket';
  import { precheckPermissionClone } from '@services/source/mysqlPermissionAuthorize';
  import type { HostInfo } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import SourceColumn from '@views/db-manage/mysql/MYSQL_CLIENT_CLONE_RULES/components/SourceColumn.vue';
  import TargetColumn from '@views/db-manage/mysql/MYSQL_CLIENT_CLONE_RULES/components/TargetColumn.vue';

  import { random } from '@utils';

  interface RowData {
    bk_cloud_id: number;
    module: string;
    source: string;
    target: string;
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: '192.168.10.1',
      key: 'source',
      label: t('源客户端IP'),
    },
    {
      case: '192.168.10.2,192.168.10.3,',
      key: 'target',
      label: t('新客户端IP'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    bk_cloud_id: data.bk_cloud_id || 0,
    module: data.module || '',
    source: data.source || '',
    target: data.target || '',
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  useTicketDetail<TendbCluster.ClientCloneRules>(TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.clone_data.map((item) =>
          createTableRow({
            bk_cloud_id: item.bk_cloud_id,
            source: item.source,
            target: item.target.join(','),
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    clone_data_list: Array<{
      message: string;
      source: string;
      target: Array<string> | string;
    }>;
    clone_type: string;
    clone_uid: string;
    message: string;
    pre_check: boolean;
  }>(TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const precheckResult = await precheckPermissionClone({
      bizId: window.PROJECT_CONFIG.BIZ_ID,
      clone_cluster_type: 'tendbcluster',
      clone_list: formData.tableData,
      clone_type: 'client',
    });
    if (precheckResult.pre_check) {
      createTicketRun({
        details: {
          ...precheckResult,
          clone_type: 'client',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditNetIp = (list: HostInfo[]) => {
    const dataList = list.reduce<RowData[]>((acc, host) => {
      acc.push(
        createTableRow({
          bk_cloud_id: host.cloud_id,
          source: host.ip,
        }),
      );
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].source ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        source: item.source,
        target: item.target,
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].source ? formData.tableData : []), ...dataList];
    }
  };
</script>
