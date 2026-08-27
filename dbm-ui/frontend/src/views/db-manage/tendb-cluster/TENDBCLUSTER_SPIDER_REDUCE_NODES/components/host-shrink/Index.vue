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
  <div class="mt-16 mb-16">
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
  </div>
  <EditableTable
    ref="table"
    class="mb-20"
    :model="tableData"
    :rules="rules">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumn
        v-model="item.spider_reduced_host"
        :handle-row-merge="handleRowMerge"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <EditableColumn
        field="spider_reduced_host.role"
        :label="t('缩容节点类型')"
        :min-width="200"
        readonly
        :rowspan="item.same_role">
        <EditableBlock
          v-model="instanceRoleMap[item.spider_reduced_host.role as keyof typeof instanceRoleMap]"
          :placeholder="t('自动生成')" />
      </EditableColumn>
      <EditableColumn
        field="spider_reduced_host.master_domain"
        :label="t('关联集群')"
        :min-width="200"
        readonly
        :rowspan="item.same_cluster">
        <EditableBlock
          v-model="item.spider_reduced_host.master_domain"
          :placeholder="t('自动生成')" />
      </EditableColumn>
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow"
        :handle-row-merge="handleRowMerge" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';

  import { random } from '@utils';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

  interface RowData {
    same_cluster: number;
    same_role: number;
    spider_reduced_host: ComponentProps<typeof HostColumn>['modelValue'];
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
        spider_reduced_hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      }[];
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
    },
  ];

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    same_cluster: data.same_cluster || 1,
    same_role: data.same_role || 1,
    spider_reduced_host: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_id: 0,
        ip: '',
        master_domain: '',
        role: '',
      },
      data.spider_reduced_host,
    ),
  });

  const tableKey = ref(random());
  const tableData = ref<RowData[]>([createTableRow()]);
  const selected = computed(() =>
    tableData.value.filter((item) => item.spider_reduced_host.ip).map((item) => item.spider_reduced_host),
  );
  const selectedMap = computed(() =>
    Object.fromEntries(tableData.value.map((cur) => [cur.spider_reduced_host.ip, true])),
  );

  const instanceRoleMap = {
    spider_master: 'Spider Master',
    spider_slave: 'Spider Slave',
  };

  // 具备完全相同的集群id列的行数组map
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};
  // 相同集群id，相同role的行数组map
  let sameRoleRowsMap: Record<string, RowData[]> = {};

  // 行合并
  const handleRowMerge = () => {
    // 接口都响应后再合并
    const isRespsoned = tableData.value.every((item) => !!item.spider_reduced_host.cluster_id);
    if (!isRespsoned) {
      return;
    }

    const sortedData = _.sortBy(tableData.value, [
      (item) => item.spider_reduced_host.cluster_id,
      (item) => item.spider_reduced_host.role,
    ]);

    sameClusterIdsRowsMap = _.groupBy(sortedData, (item) => item.spider_reduced_host.cluster_id);
    sameRoleRowsMap = _.groupBy(
      sortedData,
      (item) => `${item.spider_reduced_host.cluster_id}-${item.spider_reduced_host.role}`,
    );

    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      Object.assign(list[0], {
        same_cluster: list.length,
      });
    });
    Object.values(sameRoleRowsMap).forEach((list) => {
      Object.assign(list[0], {
        same_role: list.length,
      });
    });

    tableData.value = sortedData;
  };

  const rules = {
    'spider_reduced_host.role': [
      {
        message: t('同集群不允许同时操作 Spider Master 和 Spider Slave'),
        trigger: 'blur',
        validator: (
          value: string,
          row: {
            rowData: RowData;
            rowIndex: number;
          },
        ) =>
          sameClusterIdsRowsMap[row.rowData.spider_reduced_host.cluster_id].every(
            (item) => item.spider_reduced_host.role === value,
          ),
      },
    ],
  };

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.reduce<typeof tableData.value>((acc, item) => {
            item.old_nodes.spider_reduced_hosts.forEach((host) => {
              acc.push(
                createTableRow({
                  spider_reduced_host: {
                    ip: host.ip || '',
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
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0]!.spider_reduced_host.bk_host_id ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        spider_reduced_host: {
          ip: item.ip,
        },
      }),
    );

    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0]!.spider_reduced_host.ip ? tableData.value : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose<Exposes>({
    getValue() {
      return tableRef.value!.validate().then(() => {
        const infos = Object.entries(sameClusterIdsRowsMap).reduce<ServiceReturnType<Exposes['getValue']>['infos']>(
          (acc, [clusterId, items]) => {
            acc.push({
              cluster_id: Number(clusterId),
              old_nodes: {
                spider_reduced_hosts: items.map((item) => ({
                  bk_biz_id: item.spider_reduced_host.bk_biz_id,
                  bk_cloud_id: item.spider_reduced_host.bk_cloud_id,
                  bk_host_id: item.spider_reduced_host.bk_host_id,
                  ip: item.spider_reduced_host.ip,
                })),
              },
              reduce_spider_role: items[0]!.spider_reduced_host.role,
              spider_reduced_hosts: items.map((item) => ({
                bk_biz_id: item.spider_reduced_host.bk_biz_id,
                bk_cloud_id: item.spider_reduced_host.bk_cloud_id,
                bk_host_id: item.spider_reduced_host.bk_host_id,
                ip: item.spider_reduced_host.ip,
              })),
            });
            return acc;
          },
          [],
        );

        return {
          infos,
        };
      });
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
