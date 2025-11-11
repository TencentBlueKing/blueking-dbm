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
  <TicketInfoTable
    bordered
    :data="tableData"
    :row-class-name="generateRowClass"
    row-key="ip"
    :rowspan-and-colspan="rowspanAndColspan">
    <TicketInfoTableColumn
      col-key="ip"
      :get-copy-value="(row: RowData) => [row.ip, row.related_slave_ip || '']"
      :min-width="150"
      :title="t('目标主机')">
      <template #default="{ row: data }: { row: RowData }">
        <p class="has-related">{{ data.ip || '--' }}</p>
        <div
          v-if="data?.related_slave_ip"
          class="related-slave">
          <p>{{ t('关联 Slave') }}</p>
          <p>-- {{ data?.related_slave_ip }}</p>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="role"
      :min-width="150"
      :title="t('角色类型')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_domain"
      :min-width="250"
      :title="t('所属集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.cluster_domain || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_config"
      :min-width="200"
      :title="t('规格需求')">
      <template #default="{ row: data }: { row: RowData }">
        <SpecDetailPopover
          v-if="data.spec_config?.name"
          :data="data.spec_config">
          {{ data.spec_config?.name || '--' }}
          <DbIcon
            class="visible-icon ml-4"
            type="visible1" />
        </SpecDetailPopover>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.labels.length">
          <BkTag
            v-for="item in row.labels"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <BkTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </BkTag>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { DetailSpecs } from '@services/model/ticket/details/common';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.ClusterCutoff>;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_CUTOFF,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  interface RowData {
    cluster_domain: string;
    ip: string;
    labels: string[];
    related_slave_ip?: string; // 关联的slave
    role: string;
    spec_config: DetailSpecs[number];
  }

  const tableData = ref<RowData[]>([]);

  const generateRowClass = ({ row }: { row: RowData }) => {
    if (row.related_slave_ip) {
      return 'related-slave-row';
    }
    return '';
  };

  const spanInfo: {
    rowIndex: number;
    rowspan: number;
  }[] = [];

  const { clusters, infos, specs } = props.ticketDetails.details;
  const list = infos.flatMap((infoItem) => {
    const role = infoItem.switch_role as keyof (typeof infos)[number]['old_nodes'];
    const hosts = infoItem[role]!;

    const resouceSpecItem = Object.values(infoItem.resource_spec)[0];
    const labels = resouceSpecItem.label_names || [];
    const domain = clusters[infoItem.cluster_ids[0]].immute_domain;
    const specConfig = specs[resouceSpecItem.spec_id];
    const redisMasterOldNodes = role === 'redis_master' ? infoItem['old_nodes']['redis_master']! : [];

    return hosts.map((host, hostIndex) => ({
      cluster_domain: domain,
      ip: host.ip,
      labels,
      related_slave_ip: role === 'redis_master' ? redisMasterOldNodes[hostIndex * 2 + 1].ip : '',
      role,
      spec_config: specConfig,
    }));
  });

  const domainCounter: Record<string, number> = {};
  list.forEach((rowData, index) => {
    const domain = rowData.cluster_domain;
    domainCounter[domain] = (domainCounter[domain] || 0) + 1;
    if (domainCounter[domain] > 1) {
      spanInfo.push({
        rowIndex: index + 1 - domainCounter[domain],
        rowspan: domainCounter[domain],
      });
    }
  });
  tableData.value = list;

  const rowspanAndColspan = ({ colIndex, rowIndex }: { colIndex: number; rowIndex: number }) => {
    const spanItem = spanInfo.find((item) => [2, 3, 4].includes(colIndex) && item.rowIndex === rowIndex);
    if (spanItem) {
      return {
        rowspan: spanItem.rowspan,
      };
    }
    return {};
  };
</script>
<style lang="less">
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }

  .related-slave-row {
    .t-table__td-first-col {
      padding: 0 !important;
    }

    .has-related {
      padding: 11px 8px;
    }

    .related-slave {
      padding: 0 8px;
      line-height: 18px;
      color: #979ba5;
      background: #fafbfd;
    }
  }
</style>
