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
      class="mb-16"
      theme="info"
      :title="t('节点状态修复：修复主机上状态异常的实例，当前仅支持 Mongos 节点')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="toolbox-form mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { computed, reactive, ref, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

  defineOptions({
    name: TicketTypes.MONGODB_INSTANCE_FIX_STATUS,
  });

  interface RowData {
    host: ComponentProps<typeof HostColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    host: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
        related_instances: [],
        role: '',
        spec_config: {},
      } as unknown as RowData['host'],
      data.host,
    ),
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mongodb.InstanceFixStatus>(TicketTypes.MONGODB_INSTANCE_FIX_STATUS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            host: {
              ip: item.ip,
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      bk_cloud_id: number;
      cluster_id: number;
      dry_run: boolean;
      instance_address: string;
      ip: string;
      master_domain: string;
      port: number;
    }[];
  }>(TicketTypes.MONGODB_INSTANCE_FIX_STATUS);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          bk_cloud_id: item.host.bk_cloud_id,
          cluster_id: item.host.related_instances[0].cluster_id,
          dry_run: false,
          instance_address: item.host.related_instances[0].instance_address,
          ip: item.host.ip,
          master_domain: item.host.related_instances[0].master_domain,
          port: item.host.port,
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        host: {
          ip: item.ip,
        },
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };
</script>
