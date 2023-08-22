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
  <BkLoading :loading="loading">
    <DbOriginalTable
      :columns="columns"
      :data="tableData" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listClusterList } from '@services/redis/toolbox';
  import type { RedisMasterSlaveSwitchDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<RedisMasterSlaveSwitchDetails>
  }

  interface RowData {
    masterIp: string,
    slaveIp: string,
    clusterName: string,
    switchMode: string,
  }


  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('故障主库主机'),
      field: 'masterIp',
    },
    {
      label: t('所属集群'),
      field: 'clusterName',
    },
    {
      label: t('待切换的从库主机'),
      field: 'slaveIp',
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  const { loading } = useRequest(listClusterList, {
    onSuccess: async (r) => {
      if (r.length < 1) {
        return;
      }
      const clusterMap = r.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {} as Record<number, string>);

      tableData.value = infos.reduce((results, item) => {
        item.pairs.forEach((pair) => {
          const obj = {
            clusterName: clusterMap[item.cluster_id],
            masterIp: pair.redis_master,
            slaveIp: pair.redis_slave,
            switchMode: item.online_switch_type,
          };
          results.push(obj);
        });
        return results;
      }, [] as RowData[]);
    },
  });

</script>
