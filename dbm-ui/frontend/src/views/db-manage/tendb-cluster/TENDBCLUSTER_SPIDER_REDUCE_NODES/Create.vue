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
              :list="nodeTypeOptions"
              @change="handleChangeRole(item)" />
          </EditableColumn>
          <HybridHostColumn
            v-model:host-list="item.host.host_list"
            v-model:select-method="item.host.select_method"
            cluster-type="TendbClusterHost"
            :count="machineCount(item)"
            field="host.select_method"
            :tab-list-config="tabListConfig(item)" />
          <EditableColumn
            field="count"
            :label="t('缩容数量（台）')"
            :min-width="200">
            <div
              v-bk-tooltips="{
                content: t('手动选择主机不需要设置缩容数量'),
                disabled: item.host.select_method !== SELECT_METHODS.MANUAL,
              }"
              style="flex: 1">
              <EditableInput
                v-model="item.count"
                :disabled="item.host.select_method === SELECT_METHODS.MANUAL"
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
  import { getTendbclusterMachineList } from '@services/source/tendbcluster';

  import { useCreateTicket } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import HybridHostColumn, {
    SELECT_METHODS,
  } from '@views/db-manage/common/toolbox-field/column/hybrid-host-column/Index.vue';
  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';

  import type { PanelListType } from '@/components/instance-selector/Index.vue';

  interface RowData {
    cluster: {
      id: number;
      master_domain: string;
      role: string;
      master_count: number;
      slave_count: number;
    };
    host: {
      select_method: string;
      host_list: {
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
      master_count: 0,
      slave_count: 0,
    },
    host: data.host || {
      select_method: '',
      host_list: [],
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
      label: 'Spider Master',
    },
    {
      value: 'spider_slave',
      label: 'Spider Slave',
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

          if (item.host.host_list.length) {
            info.old_nodes = { spider_reduced_hosts: item.host.host_list };
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
              master_count: item.spider_master.length,
              slave_count: item.spider_slave.length,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleChangeRole = (row: RowData) => {
    row.host.select_method = SELECT_METHODS.AUTO;
  };

  const machineCount = (row: RowData) => {
    if (row.cluster.role === 'spider_master') {
      return row.cluster.master_count;
    }
    if (row.cluster.role === 'spider_slave') {
      return row.cluster.slave_count;
    }
    return 0;
  };

  const tabListConfig = (row: RowData) => {
    const isMater = row.cluster.role === 'spider_master';
    return {
      TendbClusterHost: [
        {
          name: t('主机选择'),
          topoConfig: {
            filterClusterId: row.cluster.id,
            countFunc: (clusterItem: TendbClusterModel) => {
              const hostList = isMater ? clusterItem.spider_master : clusterItem.spider_slave;
              const ipList = hostList.map((hostItem) => hostItem.ip);
              return new Set(ipList).size;
            },
          },
          tableConfig: {
            getTableList: (params: ServiceReturnType<typeof getTendbclusterMachineList>) =>
              getTendbclusterMachineList({
                ...params,
                spider_role: isMater ? 'spider_master' : 'spider_slave',
              }),
            firsrColumn: {
              label: isMater ? t('Master 主机') : t('Slave 主机'),
              field: 'ip',
              role: '',
            },
          },
        },
        {
          tableConfig: {
            getTableList: (params: ServiceReturnType<typeof getTendbclusterMachineList>) =>
              getTendbclusterMachineList({
                ...params,
                spider_role: isMater ? 'spider_master' : 'spider_slave',
              }),
            firsrColumn: {
              label: isMater ? t('Master 主机') : t('Slave 主机'),
              field: 'ip',
              role: '',
            },
          },
        },
      ],
    } as unknown as Record<ClusterTypes, PanelListType>;
  };
</script>
