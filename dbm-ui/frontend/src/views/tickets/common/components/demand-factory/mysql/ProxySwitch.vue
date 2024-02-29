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
    class="details-proxy-switch__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { MysqlIpItem, MySQLProxySwitchDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<MySQLProxySwitchDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type dataItem = {
    cluster_ids: number[],
    origin_proxy: MysqlIpItem,
    target_proxy: MysqlIpItem,
    immute_domain: string,
    name: string,
  }

  /**
   * mysql 替换 proxy
   */

  const columns: any = [{
    label: t('集群ID'),
    field: 'cluster_ids',
    render: ({ cell }: { cell: number }) => <span>{cell || '--'}</span>,
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
    label: t('目标Proxy主机'),
    field: 'origin_proxy',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('新Proxy主机'),
    field: 'target_proxy',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
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
            origin_proxy: item.origin_proxy.ip,
            target_proxy: item.target_proxy.ip,
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
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
