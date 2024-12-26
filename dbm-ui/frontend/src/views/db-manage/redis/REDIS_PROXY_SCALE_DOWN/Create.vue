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
      :title="t('缩容接入层：减少集群的Proxy数量，但集群Proxy数量不能少于2')" />
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumnGroup
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit"
            @change="(data) => handleInputed(data, item)" />
          <NodeTypeColumn v-model="item.nodeType.role" />
          <AutoManualHost
            v-model="item.host.type"
            field="host.type"
            :label="t('主机选择方式')"
            :min-width="150"
            :spec-ids="item.nodeType.proxy_spec_ids"
            @change="(list) => handleSelectHost(list, item)" />
          <ReducedCountColumn
            v-model="item.count"
            :disabled="item.host.type === HostSelectType.MANUAL" />
          <SwitchModeColumn
            v-model="item.switchMode"
            :disabled="item.host.type === HostSelectType.MANUAL" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <TicketRemark v-model="formData.remark" />
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

  import RedisModel from '@services/model/redis/redis';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import AutoManualHost, {
    type HostInfo,
    HostSelectType,
  } from '@views/db-manage/common/toolbox-field/host-column/AutoManualHost.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/ticket-remark/Index.vue';

  import ClusterColumnGroup from './components/ClusterColumnGroup.vue';
  import NodeTypeColumn from './components/NodeTypeColumn.vue';
  import ReducedCountColumn from './components/ReducedCountColumn.vue';
  import SwitchModeColumn from './components/SwitchModeColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      domain: string;
      cluster_type_name: string;
    };
    nodeType: {
      role: string;
      proxy_spec_ids: number[];
    };
    host: {
      type: string;
      list: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
    };
    count: string;
    switchMode: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      domain: '',
      cluster_type_name: '',
    },
    nodeType: data.nodeType || {
      role: '',
      proxy_spec_ids: [],
    },
    host: data.host || {
      type: '',
      list: [],
    },
    count: data.count || '',
    switchMode: data.switchMode || '',
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.domain, true])));

  const rules = {
    'cluster.domain': [
      {
        validator: (value: string) => selected.value.filter((item) => item.domain === value).length < 2,
        message: t('目标集群重复'),
        trigger: 'change',
      },
    ],
  };

  interface TicketDetail {
    ip_source: 'resource_pool';
    infos: {
      cluster_id: number;
      target_proxy_count?: number;
      old_nodes?: {
        proxy_reduced_hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      online_switch_type: string;
    }[];
  }

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<TicketDetail>(
    TicketTypes.REDIS_PROXY_SCALE_DOWN,
  );

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun(
      {
        ip_source: 'resource_pool',
        infos: formData.tableData.map((item) => {
          const info: TicketDetail['infos'][0] = {
            cluster_id: item.cluster.id,
            online_switch_type: item.switchMode,
          };

          if (item.host.list.length) {
            info.old_nodes = { proxy_reduced_hosts: item.host.list };
          } else if (item.count) {
            info.target_proxy_count = Number(item.count);
          }

          return info;
        }),
      },
      formData.remark,
    );
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: RedisModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              id: item.id,
              domain: item.master_domain,
              cluster_type_name: item.cluster_type_name,
            },
            nodeType: {
              role: 'Proxy',
              proxy_spec_ids: item?.proxy.map((item) => item.spec_config?.id),
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleInputed = (data: RedisModel, row: RowData) => {
    row.nodeType = {
      role: 'Proxy',
      proxy_spec_ids: data?.proxy.map((item) => item.spec_config?.id),
    };
  };

  const handleSelectHost = (list: HostInfo[], row: RowData) => {
    row.host.list = list;
  };
</script>
