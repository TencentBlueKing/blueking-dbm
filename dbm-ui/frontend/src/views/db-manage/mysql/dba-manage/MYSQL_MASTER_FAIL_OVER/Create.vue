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
      :title="t('Slave提升成主库_断开同步_切换后集成成单点状态_一般用于紧急切换')" />
    <div>
      <div class="title-spot mt-12 mb-10">{{ t('切换类型') }}<span class="required" /></div>
      <CardCheckbox
        v-model="operaObjectType"
        :desc="t('用于强制执行实例级别切换')"
        icon="rebuild"
        :title="t('实例切换')"
        :true-value="OperaObejctType.INSTANCE" />
    </div>
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
          <MasterColumn
            v-model="item.master"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SlaveColumn
            v-model="item.slave"
            :master="item.master" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.master.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('所属业务')"
            :min-width="150">
            <EditableBlock v-if="item.master.bk_biz_id">
              {{ getBizInfoById(item.master.bk_biz_id)?.name || item.master.bk_biz_id }}
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
  import { OperaObejctType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import CheckPayload, {
    createCheckPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/check-payload/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { useGlobalBizs } from '@/stores';

  import BatchInput, { type InputItem } from './components/BatchInput.vue';
  import MasterColumn, { type IValue } from './components/MasterColumn.vue';
  import SlaveColumn from './components/SlaveColumn.vue';

  interface RowData {
    master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      instance_address: string;
      ip: string;
      master_domain: string;
      port: number;
    };
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      instance_address: string;
      ip: string;
    };
  }

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    master: data.master || {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: '',
      ip: '',
      master_domain: '',
      port: 0,
    },
    slave: data.slave || {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      instance_address: '',
      ip: '',
    },
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    ...createCheckPayload(),
    ...createTickePayload(),
  });

  const operaObjectType = ref(OperaObejctType.INSTANCE);
  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.master.bk_host_id).map((item) => item.master),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  useTicketDetail<Mysql.MasterFailOver>(TicketTypes.MYSQL_MASTER_FAIL_OVER, {
    async onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        ...createCheckPayload(details),
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            master: {
              ...item.master_ip,
              cluster_id: item.cluster_ids[0],
              instance_address: `${item.master_ip.ip}:${item.master_ip.port}`,
              master_domain: clusters[item.cluster_ids[0]].immute_domain,
              port: item.master_ip.port as number,
            },
            slave: {
              ...item.slave_ip,
              instance_address: `${item.slave_ip.ip}:${item.slave_ip.port}`,
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      master_ip: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      slave_ip: {
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
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_ids: [item.master.cluster_id],
          master_ip: {
            bk_biz_id: item.master.bk_biz_id,
            bk_cloud_id: item.master.bk_cloud_id,
            bk_host_id: item.master.bk_host_id,
            ip: item.master.ip,
          },
          slave_ip: {
            bk_biz_id: item.slave.bk_biz_id,
            bk_cloud_id: item.slave.bk_cloud_id,
            bk_host_id: item.slave.bk_host_id,
            ip: item.slave.ip,
          },
        })),
        is_check_delay: formData.is_check_delay,
        is_check_process: formData.is_check_process,
        is_verify_checksum: formData.is_verify_checksum,
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: IValue[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            master: {
              bk_biz_id: item.bk_biz_id,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              instance_address: item.instance_address,
              ip: item.ip,
              master_domain: item.master_domain,
              port: item.port,
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
      if (!selectedMap.value[item.master]) {
        acc.push(
          createTableRow({
            master: {
              bk_biz_id: 0,
              bk_cloud_id: 0,
              bk_host_id: 0,
              cluster_id: 0,
              instance_address: item.master,
              ip: '',
              master_domain: '',
              port: 0,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
