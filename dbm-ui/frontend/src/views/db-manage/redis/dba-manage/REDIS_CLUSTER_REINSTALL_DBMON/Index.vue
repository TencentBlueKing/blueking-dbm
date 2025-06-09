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
      :title="t('用于批量为集群重新标准化')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16"
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
          <ClusterColumn
            v-model="item.cluster"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('所属业务')"
            :min-width="150">
            <EditableBlock v-if="item.cluster.bk_biz_id">
              {{ getBizInfoById(item.cluster.bk_biz_id)?.name || item.cluster.bk_biz_id }}
            </EditableBlock>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkCheckbox
        v-model="formData.restart_exporter"
        class="mb-16">
        {{ t('重新下发GSE配置') }}
      </BkCheckbox>
      <TicketPayload v-model="formData.ticketPayload" />
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

  import type { DeepPartial } from '@services/types';

  import { useBatchCreateTicket } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn, { type IValue } from './components/ClusterColumn.vue';

  interface RowData {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      id: number;
      master_domain: string;
    };
  }

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      id: 0,
      master_domain: '',
      ...data.cluster,
    },
  });

  const defaultData = () => ({
    restart_exporter: false,
    tableData: [createTableRow()],
    ticketPayload: createTickePayload(),
  });

  const formData = reactive(defaultData());
  const tableKey = ref(Date.now());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const { loading: isSubmitting, run: createTicketRun } = useBatchCreateTicket<{
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_ids: number[];
    is_stop: boolean;
    restart_exporter: boolean;
  }>(TicketTypes.REDIS_CLUSTER_REINSTALL_DBMON);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      bizIdExtractor: (item) => item.cluster.bk_biz_id,
      data: formData.tableData,
      detailsExtractor: (item) => ({
        bk_biz_id: item.cluster.bk_biz_id,
        bk_cloud_id: item.cluster.bk_cloud_id,
        cluster_ids: [item.cluster.id],
        is_stop: false,
        restart_exporter: formData.restart_exporter,
      }),
      ticketPayload: formData.ticketPayload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: IValue[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              bk_biz_id: item.bk_biz_id,
              bk_cloud_id: item.bk_cloud_id,
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

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          cluster: {
            master_domain: item.master_domain,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = Date.now();
      formData.tableData = [...dataList]; // 覆盖
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList]; // 追加
    }
  };
</script>
