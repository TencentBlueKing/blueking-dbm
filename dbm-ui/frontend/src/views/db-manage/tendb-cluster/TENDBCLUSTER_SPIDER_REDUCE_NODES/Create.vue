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
      :title="t('缩容接入层：减加集群的Proxy数量')" />
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
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            field="cluster.role"
            :label="t('缩容节点类型')"
            :min-width="200"
            required>
            <EditableSelect
              v-model="item.cluster.role"
              :input-search="false"
              :list="nodeTypeOptions" />
          </EditableColumn>
          <HybridHostColumn
            v-model="item.host.type"
            field="host.type"
            :label="t('主机选择方式')"
            :limit="1"
            :min-width="200"
            :spec-ids="getSpecIds(item)"
            @change="(list) => handleSelectHost(list, item)" />
          <EditableColumn
            field="count"
            :label="t('缩容数量（台）')"
            :min-width="200">
            <div
              v-bk-tooltips="{
                content: t('手动选择主机不需要设置缩容数量'),
                disabled: item.host.type !== HostSelectType.MANUAL,
              }"
              style="flex: 1">
              <EditableInput
                v-model="item.count"
                :disabled="item.host.type === HostSelectType.MANUAL"
                :min="0"
                type="number" />
            </div>
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <IgnoreBiz
        v-model="formData.isSafe"
        v-bk-tooltips="t('如忽略_有连接的情况下也会执行')" />
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

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import HybridHostColumn, {
    type HostInfo,
    HostSelectType,
  } from '@views/db-manage/common/toolbox-field/column/hybrid-host-column/Index.vue';
  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
      role: string;
      master_spec_ids: number[];
      slave_spec_ids: number[];
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
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
      role: '',
      master_spec_ids: [],
      slave_spec_ids: [],
    },
    host: data.host || {
      type: '',
      list: [],
    },
    count: data.count || '',
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    isSafe: false,
    ...createTickePayload(),
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const nodeTypeOptions = [
    {
      value: 'spider_master',
      label: 'Master',
    },
    {
      value: 'spider_slave',
      label: 'Slave',
    },
  ];

  interface TicketDetail {
    is_safe: boolean;
    infos: {
      cluster_id: number;
      reduce_spider_role: string;
      spider_reduced_to_count?: number;
      old_nodes?: {
        spider_reduced_hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
    }[];
  }

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<TicketDetail>(
    TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES,
  );

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        is_safe: formData.isSafe,
        infos: formData.tableData.map((item) => {
          const info: TicketDetail['infos'][0] = {
            cluster_id: item.cluster.id,
            reduce_spider_role: item.cluster.role,
          };

          if (item.host.list.length) {
            info.old_nodes = { spider_reduced_hosts: item.host.list };
          } else if (item.count) {
            info.spider_reduced_to_count = Number(item.count);
          }

          return info;
        }),
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
              role: '',
              master_spec_ids: item.spider_master.map((item) => item.spec_config?.id),
              slave_spec_ids: item.spider_slave.map((item) => item.spec_config?.id),
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleSelectHost = (list: HostInfo[], row: RowData) => {
    row.host.list = list;
  };

  const getSpecIds = (row: RowData) => {
    if (row.cluster.role === 'spider_master') {
      return row.cluster.master_spec_ids;
    }
    if (row.cluster.role === 'spider_slave') {
      return row.cluster.slave_spec_ids;
    }
    return [];
  };
</script>
