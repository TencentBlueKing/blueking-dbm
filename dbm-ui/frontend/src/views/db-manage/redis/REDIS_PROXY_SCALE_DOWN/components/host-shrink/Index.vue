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
      <OnlineSwitchTypeColumn
        v-model="item.online_switch_type"
        :rowspan="rowSpan[item.proxy_reduced_host.master_domain]"
        @batch-edit="handleOnlineSwitchTypeBatchEdit" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Redis } from '@services/model/ticket/ticket';

  import OnlineSwitchTypeColumn, { ONLINE_SWITCH_TYPE } from '../OnlineSwitchTypeColumn.vue';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

  interface RowData {
    online_switch_type: string;
    proxy_reduced_host: ComponentProps<typeof HostColumn>['modelValue'];
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

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    online_switch_type: data.online_switch_type || ONLINE_SWITCH_TYPE.USER_CONFIRM,
    proxy_reduced_host: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_id: 0,
        ip: '',
        master_domain: '',
        role: 'proxy',
      },
      data.proxy_reduced_host,
    ),
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

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.reduce<typeof tableData.value>((acc, item) => {
            item.old_nodes.proxy_reduced_hosts.forEach((host) => {
              acc.push(
                createTableRow({
                  online_switch_type: item.online_switch_type,
                  proxy_reduced_host: {
                    ip: host.ip,
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
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0].proxy_reduced_host.bk_host_id ? tableData.value : []), ...dataList];
  };

  const handleOnlineSwitchTypeBatchEdit = (value: string | string[]) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        online_switch_type: value,
      });
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

      const groupByCluster = _.groupBy(tableData.value, (item) => item.proxy_reduced_host.cluster_id);

      const dataList = Object.entries(groupByCluster).map(([clusterId, items]) => {
        const hostList = items.flatMap((item) => item.proxy_reduced_host);
        return {
          cluster_id: Number(clusterId),
          hostList,
          online_switch_type: items[0].online_switch_type,
        };
      });

      return {
        infos: dataList.map((item) => ({
          cluster_id: item.cluster_id,
          old_nodes: {
            proxy_reduced_hosts: item.hostList.map((item) => ({
              bk_biz_id: item.bk_biz_id,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
            })),
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
