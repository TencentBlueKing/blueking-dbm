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
    class="details-table-backup__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { MySQLProxyUpgradeDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { getPackages } from '@services/source/package';

  interface DataItem {
    cluster_id: number,
    immute_domain: string,
    name: string,
    current_version: string,
    pkg_id: number,
    target_version: string,
  }

  interface Props {
    ticketDetails: TicketModel<MySQLProxyUpgradeDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList = ref<DataItem[]>([])

  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      width: 100,
      render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
    },
    {
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
    },
    {
      label: t('当前版本'),
      field: 'current_version',
      render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('目标版本'),
      field: 'target_version',
      render: ({ cell }: { cell: [] }) => <span>{cell || '--'}</span>,
    }
  ];

  const list: DataItem[] = [];
  const infosData = props.ticketDetails?.details?.infos || [];
  const clusterIds = props.ticketDetails?.details?.clusters || {};
  infosData.forEach((item) => {
    item.cluster_ids.forEach((id) => {
      const clusterData = clusterIds[id];
      list.push(Object.assign({
        cluster_id: id,
        immute_domain: clusterData.immute_domain,
        name: clusterData.name,
        current_version: item.display_info.current_version,
        pkg_id: item.pkg_id,
        target_version: '',
      }));
    });
  });
  dataList.value = list

  useRequest(getPackages, {
    defaultParams: [{
      pkg_type: 'mysql-proxy',
      db_type: 'mysql'
    }],
    onSuccess(packageResult) {
      const packageMap = packageResult.results.reduce((prev, item) => Object.assign(prev, { [item.id]: item.name }), {} as Record<number, string>)
      dataList.value = dataList.value.map(item => Object.assign(item, { target_version: packageMap[item.pkg_id] }))
    }
  })
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
