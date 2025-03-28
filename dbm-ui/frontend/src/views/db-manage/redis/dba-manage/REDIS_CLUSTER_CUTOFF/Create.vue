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
      :title="t('用于批量执行整机替换')" />
    <BatchInput @change="handleBatchInput" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('角色类型')"
            :min-width="150">
            <EditableBlock
              v-model="item.host.role"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.host.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('所属业务')"
            :min-width="150">
            <EditableBlock v-if="item.host.bk_biz_id">
              {{ getBizInfoById(item.host.bk_biz_id)?.name || item.host.bk_biz_id }}
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
      <CheckPayload v-model="formData" />
      <TicketPayload v-model="formData" />
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

  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CheckPayload, {
    createCheckPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/check-payload/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { useGlobalBizs } from '@/stores';

  import BatchInput, { type InputItem } from './components/BatchInput.vue';
  import HostColumn, { type IValue } from './components/HostColumn.vue';

  interface RowData {
    host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      master_domain: string;
      role: string;
    };
  }

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    host: data.host || {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      ip: '',
      master_domain: '',
      role: '',
    },
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    ...createCheckPayload(),
    ...createTickePayload(),
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mysql.MasterFailOver>(TicketTypes.MYSQL_MASTER_FAIL_OVER, {
    async onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      const { clusters, infos } = details;
      Object.assign(formData, {
        ...createCheckPayload(details),
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            host: {
              ...item.master_ip,
              cluster_id: item.cluster_ids[0],
              master_domain: clusters[item.cluster_ids[0]].immute_domain,
              role: '',
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      master_ip: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }[];
    is_check_delay: boolean;
    is_check_process: boolean;
    is_verify_checksum: boolean;
  }>(TicketTypes.MYSQL_MASTER_FAIL_OVER, {
    isDbaTool: true,
  });

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const infosByBiz = formData.tableData.reduce<Record<number, Mysql.MasterFailOver['infos']>>((acc, item) => {
      const currentBizId = item.host.bk_biz_id;
      Object.assign(acc, {
        [currentBizId]: [
          ...(acc[currentBizId] || []),
          {
            cluster_ids: [item.host.cluster_id],
            master_ip: {
              bk_biz_id: item.host.bk_biz_id,
              bk_cloud_id: item.host.bk_cloud_id,
              bk_host_id: item.host.bk_host_id,
              ip: item.host.ip,
            },
          },
        ],
      });
      return acc;
    }, {});

    const data = Object.entries(infosByBiz).map(([bizId, infos]) => {
      return {
        bk_biz_id: Number(bizId),
        details: {
          infos,
          is_check_delay: formData.is_check_delay,
          is_check_process: formData.is_check_process,
          is_verify_checksum: formData.is_verify_checksum,
        },
        remark: formData.remark,
        ticket_type: TicketTypes.MYSQL_MASTER_FAIL_OVER,
      };
    });

    console.log(data);
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: IValue[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              bk_biz_id: item.bk_biz_id,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              ip: item.ip,
              master_domain: item.master_domain,
              role: item.role,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: InputItem[]) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              bk_biz_id: 0,
              bk_cloud_id: 0,
              bk_host_id: 0,
              cluster_id: 0,
              ip: item.ip,
              master_domain: '',
              role: '',
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
