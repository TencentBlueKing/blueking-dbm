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
  <DbOriginalTable
    class="details-master-fail__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { computed, type PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { MysqlIpItem, MySQLMasterFailDetails, TicketDetails } from '@services/types/ticket';

  const props = defineProps({
    ticketDetails: {
      required: true,
      type: Object as PropType<TicketDetails<MySQLMasterFailDetails>>,
    },
  });

  const { t } = useI18n();

  type dataItem = {
    cluster_ids: number,
    master_ip: MysqlIpItem,
    slave_ip: MysqlIpItem,
    immute_domain: string,
    name: string,
  }

  /**
   *  MySQL 主故障切换
   */

  const columns: any = [{
    label: t('集群ID'),
    field: 'cluster_ids',
    render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
  }, {
    label: t('集群名称'),
    field: 'immute_domain',
    showOverflowTooltip: false,
    render: ({ data }: { data: any }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.immute_domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.immute_domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
  }, {
    label: t('故障主库IP'),
    field: 'master_ip',
    render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
  }, {
    label: t('从库IP'),
    field: 'slave_ip',
    render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
  }];

  const dataList = computed(() => {
    const list: dataItem[] = [];
    const infosData = props.ticketDetails?.details?.infos || [];
    const clusterIds = props.ticketDetails?.details?.clusters || {};
    infosData.forEach((item) => {
      if (item.cluster_ids) {
        item.cluster_ids.forEach((id) => {
          const clusterData = clusterIds[id];
          list.push(Object.assign({
            cluster_ids: id,
            master_ip: item.master_ip.ip,
            slave_ip: item.slave_ip.ip,
            immute_domain: clusterData.immute_domain,
            name: clusterData.name,
          }));
        });
      }
    });
    return list;
  });
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
</style>
