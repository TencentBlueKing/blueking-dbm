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
      :title="t('DB 实例权限克隆：DB 实例 IP 替换时，克隆原实例的所有权限到新实例中')" />
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
            v-model:cluster-domain="item.cluster_domain"
            v-model:source="item.source"
            @batch-edit="handleBatchEdit" />
          <TargetColumn
            v-model="item.target"
            :source="item.source"
            :table-data="formData.tableData" />
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

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import type { Mysql } from '@services/model/ticket/ticket';
  import { precheckPermissionClone } from '@services/source/mysqlPermissionAuthorize';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import SourceColumn from './components/SourceColumn.vue';
  import TargetColumn from './components/TargetColumn.vue';

  interface RowData {
    bk_cloud_id: number;
    cluster_domain: string;
    source: string;
    target: string;
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: '192.168.10.1:20000',
      key: 'source',
      label: t('源实例'),
    },
    {
      case: '192.168.10.2:20001,192.168.10.2:20002',
      key: 'target',
      label: t('新实例'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    bk_cloud_id: data.bk_cloud_id || 0,
    cluster_domain: data.cluster_domain || '',
    source: data.source || '',
    target: data.target || '',
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  useTicketDetail<Mysql.InstanceCloneRules>(TicketTypes.MYSQL_INSTANCE_CLONE_RULES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.clone_data.map((item) =>
          createTableRow({
            source: item.source,
            target: item.target,
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
  }>(TicketTypes.MYSQL_INSTANCE_CLONE_RULES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const precheckResult = await precheckPermissionClone({
      bizId: window.PROJECT_CONFIG.BIZ_ID,
      clone_cluster_type: 'mysql',
      clone_list: formData.tableData,
      clone_type: 'instance',
    });
    if (precheckResult.pre_check) {
      createTicketRun({
        details: {
          ...precheckResult,
          clone_type: 'instance',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbhaInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, instance) => {
      acc.push(
        createTableRow({
          bk_cloud_id: instance.bk_cloud_id,
          source: instance.instance_address,
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
