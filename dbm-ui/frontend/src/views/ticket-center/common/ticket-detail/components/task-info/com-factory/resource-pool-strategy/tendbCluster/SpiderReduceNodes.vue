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
  <InfoList>
    <InfoItem :label="t('缩容方式')">
      {{ ticketDetails.details.shrink_type === 'HOST' ? t('指定主机缩容') : t('指定数量缩容') }}
    </InfoItem>
  </InfoList>
  <BkTable
    v-if="ticketDetails.details.shrink_type === 'HOST'"
    :data="tableData"
    :merge-cells="mergeCells">
    <BkTableColumn
      field="ip"
      :label="t('目标主机')"
      :min-width="200" />
    <BkTableColumn
      field="role"
      :label="t('缩容节点类型')"
      :min-width="150" />
    <BkTableColumn
      field="domain"
      :label="t('关联集群')"
      :min-width="250" />
  </BkTable>
  <BkTable
    v-else
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('缩容节点类型')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.reduce_spider_role === 'spider_master' ? 'Spider Master' : 'Spider Slave' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前数量(台)')"
      :min-width="100">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.spider_reduced_hosts.length + data.spider_reduced_to_count }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('缩容数量(台)')"
      :min-width="100">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.spider_reduced_hosts.length }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="spider_reduced_to_count"
      :label="t('剩余数量(台)')"
      :min-width="100" />
  </BkTable>
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.is_safe ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { VxeTablePropTypes } from '@blueking/vxe-table';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderReduceNodes>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface HostTableRow {
    domain: string;
    ip: string;
    role: string;
  }

  const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  const tableData = shallowRef<HostTableRow[]>([]);

  watchEffect(() => {
    const { clusters, infos } = props.ticketDetails.details;

    tableData.value = infos.flatMap((item) =>
      item.old_nodes.spider_reduced_hosts.map((host) => ({
        domain: clusters[item.cluster_id]?.immute_domain || '--',
        ip: host.ip,
        role: item.reduce_spider_role === 'spider_master' ? 'Spider Master' : 'Spider Slave',
      })),
    );

    const domainCounts = tableData.value.reduce<Record<string, number>>((acc, { domain }) => {
      Object.assign(acc, { [domain]: (acc[domain] || 0) + 1 });
      return acc;
    }, {});

    let rowIndex = 0;
    mergeCells.value = Object.entries(domainCounts).map(([_key, count]) => {
      const mergeCell = { col: 2, colspan: 1, row: rowIndex, rowspan: count };
      rowIndex += count;
      return mergeCell;
    });
  });
</script>
