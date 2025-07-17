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
          <SpecColumn
            v-model="item.host.spec_id"
            :cluster-type="ClusterTypes.TENDBCLUSTER" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
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
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

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
      data.host,
    ),
  });

  const defaultData = () => ({
    is_safe: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

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
    is_safe: boolean;
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
        is_safe: formData.is_safe,
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
      formData.tableData = [...(formData.tableData[0].host.bk_host_id ? formData.tableData : []), ...dataList];
    }
  };
</script>
