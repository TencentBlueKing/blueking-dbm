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
      :title="t('替换接入层：对集群的接入层进行替换，支持Spider Master 和Slave')" />
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
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <SpecColumn v-model="item.host.spec_id" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
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
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';
  import SpecColumn from './components/SpecColumn.vue';

  interface RowData {
    host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      instance_address: string;
      ip: string;
      master_domain: string;
      port: number;
      role: string;
      spec_id: number;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const tableKey = ref(Date.now());

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    host: data.host || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: '',
      ip: '',
      master_domain: '',
      port: 0,
      role: '',
      spec_id: 0,
    },
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<TendbCluster.ResourcePool.SpiderSwitchNodes>(TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) => {
          const [host] = item.spider_old_ip_list;
          const cluster = clusters[item.cluster_id];
          return createTableRow({
            host: {
              ...host,
              bk_biz_id: ticketDetail.bk_biz_id,
              cluster_id: cluster.id,
              instance_address: `${host.ip}:${host.port}`,
              master_domain: cluster.immute_domain,
              role: item.switch_spider_role,
              spec_id: item.resource_spec[`${item.switch_spider_role}_${host.ip}`].spec_id,
            },
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      resource_spec: {
        [x in string]: {
          count: number;
          labels: string[];
          spec_id: number;
        };
      };
      spider_old_ip_list: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      }[];
      switch_spider_role: string;
    }[];
    ip_source: 'resource_pool';
    old_nodes: {
      spider_master: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
      spider_slave: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
  }>(TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const oldNodes = _.groupBy(formData.tableData, (item) => item.host.role);
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_id: item.host.cluster_id,
          resource_spec: {
            [`${item.host.role}_${item.host.ip}`]: {
              count: 1,
              labels: [],
              spec_id: item.host.spec_id,
            },
          },
          spider_old_ip_list: [
            {
              bk_cloud_id: item.host.bk_cloud_id,
              bk_host_id: item.host.bk_host_id,
              ip: item.host.ip,
              port: item.host.port,
            },
          ],
          switch_spider_role: item.host.role,
        })),
        ip_source: 'resource_pool',
        old_nodes: {
          spider_master: (oldNodes['spider_master'] || []).map((item) => ({
            bk_cloud_id: item.host.bk_cloud_id,
            bk_host_id: item.host.bk_host_id,
            ip: item.host.ip,
          })),
          spider_slave: (oldNodes['spider_slave'] || []).map((item) => ({
            bk_cloud_id: item.host.bk_cloud_id,
            bk_host_id: item.host.bk_host_id,
            ip: item.host.ip,
          })),
        },
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              instance_address: item.instance_address,
              ip: item.ip,
              master_domain: item.master_domain,
              port: item.port,
              role: item.role,
              spec_id: item.spec_config.id,
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
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: 0,
          bk_host_id: 0,
          cluster_id: 0,
          instance_address: '',
          ip: item.ip,
          master_domain: '',
          port: 0,
          role: '',
          spec_id: 0,
        },
      }),
    );

    if (isClear) {
      tableKey.value = Date.now();
      formData.tableData = [...dataList]; // 覆盖
    } else {
      formData.tableData = [...(formData.tableData[0].host.bk_host_id ? formData.tableData : []), ...dataList]; // 追加
    }
  };
</script>
