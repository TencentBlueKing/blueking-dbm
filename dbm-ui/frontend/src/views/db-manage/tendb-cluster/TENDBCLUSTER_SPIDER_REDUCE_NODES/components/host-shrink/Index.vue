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
    :key="tableData.length"
    ref="table"
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumn
        v-model="item.spider_reduced_host"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <EditableColumn
        field="spider_reduced_host.role"
        :label="t('缩容节点类型')"
        :min-width="200">
        <EditableBlock
          v-model="instanceRoleMap[item.spider_reduced_host.role as keyof typeof instanceRoleMap]"
          :placeholder="t('自动生成')" />
      </EditableColumn>
      <EditableColumn
        field="spider_reduced_host.master_domain"
        :label="t('关联集群')"
        :min-width="200"
        :rowspan="rowSpan[item.spider_reduced_host.master_domain]">
        <EditableBlock
          v-model="item.spider_reduced_host.master_domain"
          :placeholder="t('自动生成')" />
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

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

  interface RowData {
    spider_reduced_host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      master_domain: string;
      role: string;
    };
  }

  interface Props {
    ticketDetails?: TendbCluster.ResourcePool.SpiderReduceNodes;
  }

  interface Exposes {
    getValue: () => Promise<{
      infos: {
        cluster_id: number;
        old_nodes: {
          spider_reduced_hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
        };
        reduce_spider_role: string;
      }[];
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    spider_reduced_host: data.spider_reduced_host || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      ip: '',
      master_domain: '',
      role: '',
    },
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const selected = computed(() =>
    tableData.value.filter((item) => item.spider_reduced_host.ip).map((item) => item.spider_reduced_host),
  );
  const selectedMap = computed(() =>
    Object.fromEntries(tableData.value.map((cur) => [cur.spider_reduced_host.ip, true])),
  );
  const rowSpan = computed(() =>
    tableData.value.reduce<Record<string, number>>((acc, item) => {
      if (item.spider_reduced_host.master_domain) {
        Object.assign(acc, {
          [item.spider_reduced_host.master_domain]: (acc[item.spider_reduced_host.master_domain] || 0) + 1,
        });
      }
      return acc;
    }, {}),
  );

  /**
   * 前端展示的值
   * key 是集群带出的role
   */
  const instanceRoleMap = {
    spider_master: 'Spider Master',
    spider_slave: 'Spider Slave',
  };

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.reduce<typeof tableData.value>((acc, item) => {
            const clusterInfo = clusters[item.cluster_id];
            item.old_nodes.spider_reduced_hosts.forEach((host) => {
              acc.push(
                createTableRow({
                  spider_reduced_host: {
                    bk_biz_id: host.bk_biz_id,
                    bk_cloud_id: host.bk_cloud_id,
                    bk_host_id: host.bk_host_id,
                    cluster_id: clusterInfo.id,
                    ip: host.ip,
                    master_domain: clusterInfo.immute_domain,
                    role: item.reduce_spider_role,
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
            spider_reduced_host: {
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
    tableData.value = [...(tableData.value[0].spider_reduced_host.bk_host_id ? tableData.value : []), ...dataList];
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
          cluster_id: item.spider_reduced_host.cluster_id,
          old_nodes: {
            spider_reduced_hosts: [
              {
                bk_biz_id: item.spider_reduced_host.bk_biz_id,
                bk_cloud_id: item.spider_reduced_host.bk_cloud_id,
                bk_host_id: item.spider_reduced_host.bk_host_id,
                ip: item.spider_reduced_host.ip,
              },
            ],
          },
          reduce_spider_role: item.spider_reduced_host.role,
        })),
      };
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
