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
      <ClusterColumn
        v-model="item.cluster"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <RoleColumn
        v-model="item.cluster.role"
        @batch-edit="handleRoleBatchEdit"
        @change="handleChange(item)" />
      <EditableColumn
        :label="t('当前数量（台）')"
        :min-width="200">
        <EditableBlock :placeholder="t('自动生成')">
          {{
            !item.cluster.id
              ? ''
              : item.cluster.role === 'spider_master'
                ? item.cluster.master_count
                : item.cluster.slave_count
          }}
        </EditableBlock>
      </EditableColumn>
      <ReducedCountColumn
        v-model="item.reduced_count"
        :cluster="item.cluster"
        @batch-edit="handleRedecedCountBatchEdit"
        @change="handleChange(item)" />
      <EditableColumn
        :append-rules="targetCountRules"
        field="spider_reduced_to_count"
        :label="t('剩余数量（台）')"
        :min-width="200">
        <EditableBlock
          v-model="item.spider_reduced_to_count"
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import ClusterColumn from './components/ClusterColumn.vue';
  import ReducedCountColumn from './components/ReducedCountColumn.vue';
  import RoleColumn from './components/RoleColumn.vue';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    reduced_count: string;
    spider_reduced_to_count: string;
  }

  interface Props {
    ticketDetails?: TendbCluster.ResourcePool.SpiderReduceNodes;
  }

  interface Exposes {
    getValue: () => Promise<{
      infos: {
        cluster_id: number;
        reduce_spider_role: string;
        spider_reduced_to_count: number;
      }[];
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_count: 0,
        master_domain: '',
        role: '',
        slave_count: 0,
      },
      data.cluster,
    ),
    reduced_count: data.reduced_count || '',
    spider_reduced_to_count: data.spider_reduced_to_count || '',
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(tableData.value.map((cur) => [cur.cluster.master_domain, true])),
  );

  const targetCountRules = [
    {
      message: '',
      trigger: 'change',
      validator: (value: string, { rowData }: Record<string, any>) => {
        if (!value) {
          return true;
        }
        if (Number(value) < 2 && rowData.cluster.role === 'spider_master') {
          return t('请保证缩容后的接入层 Spider Master 数量 >= 2');
        }
        if (Number(value) < 1 && rowData.cluster.role === 'spider_slave') {
          return t('请保证缩容后的接入层 Spider Slave数量 >= 1');
        }
        return true;
      },
    },
  ];

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            const clusterInfo = clusters[item.cluster_id];
            return createTableRow({
              // 集群缺失信息会被ClusterColumn组件会填
              cluster: {
                master_domain: clusterInfo.immute_domain,
              },
              reduced_count: `${item.old_nodes.spider_reduced_hosts.length}`,
              spider_reduced_to_count: `${item.spider_reduced_to_count}`,
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
            },
            spider_reduced_to_count: `${item.spider_master.length}`,
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0].cluster.id ? tableData.value : []), ...dataList];
  };

  const handleChange = (row: RowData) => {
    if (row.cluster.role === 'spider_master') {
      Object.assign(row, {
        spider_reduced_to_count: row.cluster.master_count - (Number(row.reduced_count) || 0),
      });
    }
    if (row.cluster.role === 'spider_slave') {
      Object.assign(row, {
        spider_reduced_to_count: row.cluster.slave_count - (Number(row.reduced_count) || 0),
      });
    }
  };

  const handleRoleBatchEdit = (value: string | string[]) => {
    tableData.value.forEach((item) => {
      Object.assign(item.cluster, {
        role: value,
      });
      handleChange(item);
    });
  };

  const handleRedecedCountBatchEdit = (value: string | string[]) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        reduced_count: value,
      });
      handleChange(item);
    });
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
          cluster_id: item.cluster.id,
          reduce_spider_role: item.cluster.role,
          spider_reduced_to_count: Number(item.spider_reduced_to_count),
        })),
      };
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
