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
  <EditableTable
    ref="table"
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumn
        v-model="item.proxy_reduced_host"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <EditableColumn
        field="proxy_reduced_host.master_domain"
        :label="t('关联集群')"
        :min-width="200"
        :rowspan="rowSpan[item.proxy_reduced_host.master_domain]">
        <EditableBlock
          v-model="item.proxy_reduced_host.master_domain"
          :placeholder="t('自动生成')" />
      </EditableColumn>
      <EditableColumn
        field="online_switch_type"
        :label="t('切换模式')"
        :min-width="150">
        <EditableSelect
          v-model="item.online_switch_type"
          :input-search="false"
          :list="switchModeOptions" />
      </EditableColumn>
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Redis } from '@services/model/ticket/ticket';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

  interface RowData {
    online_switch_type: string;
    proxy_reduced_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      master_domain: string;
    };
  }

  interface Props {
    ticketDetails?: Redis.ResourcePool.ProxyScaleDown;
  }

  interface Exposes {
    getValue: () => Promise<{
      infos: {
        cluster_id: number;
        old_nodes: {
          proxy_reduced_hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
        };
        online_switch_type: string;
      }[];
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    online_switch_type: data.online_switch_type || 'user_confirm',
    proxy_reduced_host: data.proxy_reduced_host || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      ip: '',
      master_domain: '',
    },
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const selected = computed(() =>
    tableData.value.filter((item) => item.proxy_reduced_host.ip).map((item) => item.proxy_reduced_host),
  );
  const selectedMap = computed(() =>
    Object.fromEntries(tableData.value.map((cur) => [cur.proxy_reduced_host.ip, true])),
  );
  const rowSpan = computed(() =>
    tableData.value.reduce<Record<string, number>>((acc, item) => {
      if (item.proxy_reduced_host.master_domain) {
        Object.assign(acc, {
          [item.proxy_reduced_host.master_domain]: (acc[item.proxy_reduced_host.master_domain] || 0) + 1,
        });
      }
      return acc;
    }, {}),
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

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.reduce<typeof tableData.value>((acc, item) => {
            const clusterInfo = clusters[item.cluster_id];
            item.old_nodes.proxy_reduced_hosts.forEach((host) => {
              acc.push(
                createTableRow({
                  proxy_reduced_host: {
                    bk_biz_id: host.bk_biz_id,
                    bk_cloud_id: host.bk_cloud_id,
                    bk_host_id: host.bk_host_id,
                    cluster_id: clusterInfo.id,
                    ip: host.ip,
                    master_domain: clusterInfo.immute_domain,
                  },
                }),
              );
            });
            return acc;
          }, []);
        }
      }
    },
  );

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            online_switch_type: item.online_switch_type,
            proxy_reduced_host: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.related_clusters[0].id,
              ip: item.ip,
              master_domain: item.related_clusters[0].immute_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0].proxy_reduced_host.bk_host_id ? tableData.value : []), ...dataList];
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return {
          infos: [],
        };
      }

      return {
        infos: tableData.value.map((item) => ({
          cluster_id: item.proxy_reduced_host.cluster_id,
          old_nodes: {
            proxy_reduced_hosts: [
              {
                bk_biz_id: item.proxy_reduced_host.bk_biz_id,
                bk_cloud_id: item.proxy_reduced_host.bk_cloud_id,
                bk_host_id: item.proxy_reduced_host.bk_host_id,
                ip: item.proxy_reduced_host.ip,
              },
            ],
          },
          online_switch_type: item.online_switch_type,
        })),
      };
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
