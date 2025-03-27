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
    <div class="mb-16">
      <div class="title-spot mt-12 mb-10">{{ t('切换类型') }}<span class="required" /></div>
      <CardCheckbox
        v-model="operaObjectType"
        :desc="t('用于强制执行实例级别切换')"
        icon="rebuild"
        :title="t('实例切换')"
        :true-value="OperaObejctType.INSTANCE" />
    </div>
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
      <CheckPayload v-model="formData.checkPayload" />
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

  import type { TendbCluster } from '@services/model/ticket/ticket';
  import { OperaObejctType } from '@services/types';

  import { useBatchCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import CheckPayload, {
    createCheckPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/check-payload/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { useGlobalBizs } from '@/stores';

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
      port: number;
    };
  }

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: 'Master',
      regExp: ipv4,
      required: true,
    },
  ];

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
      port: 0,
    },
  });

  const defaultData = () => ({
    checkPayload: createCheckPayload(),
    tableData: [createTableRow()],
    ticketPayload: createTickePayload(),
  });

  const operaObjectType = ref(OperaObejctType.INSTANCE);
  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.master.bk_host_id).map((item) => item.master),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  useTicketDetail<TendbCluster.MasterFailOver>(TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER, {
    async onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        ...createCheckPayload(details),
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const [{ master, slave }] = item.switch_tuples;
          return createTableRow({
            master: {
              ...master,
              cluster_id: item.cluster_id,
              instance_address: `${master.ip}:${master.port}`,
              master_domain: clusters[item.cluster_id].immute_domain,
              port: master.port as number,
            },
            slave: {
              ...slave,
              instance_address: `${slave.ip}:${slave.port}`,
            },
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useBatchCreateTicket<{
    infos: {
      cluster_id: number;
      switch_tuples: {
        master: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port?: number;
        };
        slave: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port?: number;
        };
      }[];
    }[];
    is_check_delay: boolean;
    is_check_process: boolean;
    is_verify_checksum: boolean;
  }>(TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }

    createTicketRun({
      array: formData.tableData,
      keyExtractor: (item) => item.master.bk_biz_id,
      ticketPayload: formData.ticketPayload,
      translate: (item) => ({
        infos: [
          {
            cluster_id: item.master.cluster_id,
            switch_tuples: [
              {
                master: item.master,
                slave: item.slave,
              },
            ],
          },
        ],
        ...formData.checkPayload,
      }),
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

  const handleBatchInput = (data: Record<string, any>[]) => {
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
