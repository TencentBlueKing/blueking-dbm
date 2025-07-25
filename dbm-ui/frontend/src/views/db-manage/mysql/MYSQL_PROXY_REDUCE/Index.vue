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
      :title="t('缩容接入层：减少集群的Proxy数量')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MasterColumn
            v-model="item.master"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem
        v-bk-tooltips="t('存在业务连接时需要人工确认')"
        class="fit-content">
        <BkCheckbox
          v-model="formData.is_safe"
          :false-label="false"
          true-label>
          <span class="safe-action-text">{{ t('检查业务连接') }}</span>
        </BkCheckbox>
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import MasterColumn, { type SelectorHost } from './components/MasterColumn.vue';

  interface RowData {
    master: ComponentProps<typeof MasterColumn>['modelValue'];
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
    master: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        related_clusters: [] as RowData['master']['related_clusters'],
        role: '',
      },
      data.master,
    ),
  });

  const defaultData = () => ({
    is_safe: false,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.master.bk_host_id).map((item) => item.master),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mysql.ProxyReduce>(TicketTypes.MYSQL_PROXY_REDUCE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        is_safe: details.is_safe,
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            master: {
              ip: item.origin_proxy_ip.ip,
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      old_nodes: {
        origin_proxy: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      origin_proxy_ip: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }[];
    is_safe: boolean;
  }>(TicketTypes.MYSQL_PROXY_REDUCE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_ids: item.master.related_clusters.map((item) => item.id),
          old_nodes: {
            origin_proxy: [item.master],
          },
          origin_proxy_ip: item.master,
        })),
        is_safe: formData.is_safe,
      },
      ...formData.payload,
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
            master: {
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
        master: {
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
