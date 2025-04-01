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
            field="cluster.cluster_type_name"
            :label="t('架构版本')"
            :min-width="150">
            <EditableBlock
              v-model="item.cluster.cluster_type_name"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            field="cluster.role"
            :label="t('缩容节点类型')"
            :min-width="150"
            required>
            <EditableBlock
              v-model="item.cluster.role"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <HybridHostColumn
            v-model:host-list="item.host.host_list"
            v-model:select-method="item.host.select_method"
            :cluster-type="ClusterTypes.REDIS"
            :count="item.cluster.proxyCount"
            field="host.select_method"
            :tab-list-config="tabListConfig" />
          <EditableColumn
            field="count"
            :label="t('缩容数量（台）')"
            :min-width="150">
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
          <EditableColumn
            field="online_switch_type"
            :label="t('切换模式')"
            :min-width="150">
            <EditableSelect
              v-model="item.online_switch_type"
              :disabled="item.host.select_method === SELECT_METHODS.MANUAL"
              :input-search="false"
              :list="switchModeOptions" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import HybridHostColumn, {
    type PanelListType,
    SELECT_METHODS,
  } from '@views/db-manage/common/toolbox-field/column/hybrid-host-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    cluster: {
      cluster_type_name: string;
      id: number;
      master_domain: string;
      proxyCount: number;
      role: string;
    };
    count: string;
    host: {
      host_list: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
      select_method: string;
    };
    online_switch_type: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const tabListConfig = {
    [ClusterTypes.REDIS]: [
      {
        id: 'redis',
        name: t('目标从库主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Proxy 主机'),
            role: 'proxy',
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Proxy 主机'),
            role: 'proxy',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      cluster_type_name: '',
      id: 0,
      master_domain: '',
      proxyCount: 0,
      role: '',
    },
    count: data.count || '',
    host: data.host || {
      host_list: [],
      select_method: '',
    },
    online_switch_type: data.online_switch_type || '',
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  const switchModeOptions = [
    {
      label: t('需人工确认'),
      value: 'user_confirm',
    },
    {
      label: t('无需确认'),
      value: 'no_confirm',
    },
  ];

  useTicketDetail<Redis.ResourcePool.ProxyScaleDown>(TicketTypes.REDIS_PROXY_SCALE_DOWN, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterInfo = clusters[item.cluster_id];
          return createTableRow({
            cluster: {
              cluster_type_name: clusterInfo.cluster_type_name,
              id: clusterInfo.id,
              master_domain: clusterInfo.immute_domain,
              proxyCount: 0,
              role: 'Proxy',
            },
            count: `${item.target_proxy_count}`,
            host: {
              host_list: item.old_nodes.proxy_reduced_hosts,
              select_method:
                item.old_nodes.proxy_reduced_hosts.length > 0 ? SELECT_METHODS.MANUAL : SELECT_METHODS.AUTO,
            },
            online_switch_type: item.online_switch_type,
          });
        }),
      });
    },
  });

  interface TicketDetail {
    infos: {
      cluster_id: number;
      old_nodes?: {
        proxy_reduced_hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      online_switch_type: string;
      target_proxy_count?: number;
    }[];
    ip_source: 'resource_pool';
  }

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<TicketDetail>(
    TicketTypes.REDIS_PROXY_SCALE_DOWN,
  );

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => {
          const info: TicketDetail['infos'][0] = {
            cluster_id: item.cluster.id,
            online_switch_type: item.online_switch_type,
          };

          if (item.host.host_list.length) {
            info.old_nodes = { proxy_reduced_hosts: item.host.host_list };
          } else if (item.count) {
            info.target_proxy_count = item.cluster.proxyCount - Number(item.count);
          }

          return info;
        }),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
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
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
              proxyCount: item.proxyCount,
              role: 'Proxy',
            },
            host: {
              host_list: [],
              select_method: SELECT_METHODS.AUTO,
            },
            online_switch_type: 'user_confirm',
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };
</script>
