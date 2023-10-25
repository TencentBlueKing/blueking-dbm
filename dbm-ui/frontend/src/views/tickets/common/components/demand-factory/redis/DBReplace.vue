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

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { listClusterList } from '@services/redis/toolbox';
  import { getResourceSpecList } from '@services/resourceSpec';
  import type { RedisDBReplaceDetails, TicketDetails } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  interface Props {
    ticketDetails: TicketDetails<RedisDBReplaceDetails>
  }

  interface RowData {
    ip: string,
    role: string,
    clusterName: string,
    clusterType: string,
    sepc: {
      id: number,
      name: string,
    },
  }


  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('待替换的主机'),
      field: 'ip',
      showOverflowTooltip: true,
    },
    {
      label: t('角色类型'),
      field: 'role',
    },
    {
      label: t('所属集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('规格需求'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
  ];

  const { loading } = useRequest(listClusterList, {
    defaultParams: [currentBizId],
    onSuccess: async (r) => {
      if (r.length < 1) {
        return;
      }
      const clusterMap = r.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: {
          clusterName: item.master_domain,
          clusterType: item.cluster_spec.spec_cluster_type,
        } });
        return obj;
      }, {} as Record<number, {clusterName: string, clusterType: string}>);


      // 避免重复查询
      const clusterTypes = [...new Set(Object.values(clusterMap).map(item => item.clusterType))];

      const sepcMap: Record<string, ResourceSpecModel[]> = {};

      await Promise.all(clusterTypes.map(async (type) => {
        const ret = await getResourceSpecList({
          spec_cluster_type: type,
          limit: -1,
          offset: 0,
        });
        sepcMap[type] = ret.results;
      }));
      loading.value = false;
      tableData.value = infos.reduce((results, item) => {
        const sepcList = sepcMap[clusterMap[item.cluster_id].clusterType];
        if (item.proxy.length > 0) {
          item.proxy.forEach((proxyItem) => {
            const specInfo = sepcList.find(row => row.spec_id === proxyItem.spec_id);
            const obj = {
              ip: proxyItem.ip,
              role: 'Proxy',
              clusterName: clusterMap[item.cluster_id].clusterName,
              clusterType: clusterMap[item.cluster_id].clusterType,
              sepc: {
                id: proxyItem.spec_id,
                name: specInfo ? specInfo.spec_name : '',
              },
            };
            results.push(obj);
          });
        }
        if (item.redis_master.length > 0) {
          item.redis_master.forEach((masterItem) => {
            const specInfo = sepcList.find(row => row.spec_id === masterItem.spec_id);
            const obj = {
              ip: masterItem.ip,
              role: 'Master',
              clusterName: clusterMap[item.cluster_id].clusterName,
              clusterType: clusterMap[item.cluster_id].clusterType,
              sepc: {
                id: masterItem.spec_id,
                name: specInfo ? specInfo.spec_name : '',
              },
            };
            results.push(obj);
          });
        }
        if (item.redis_slave.length > 0) {
          item.redis_slave.forEach((slaveItem) => {
            const specInfo = sepcList.find(row => row.spec_id === slaveItem.spec_id);
            const obj = {
              ip: slaveItem.ip,
              role: 'Slave',
              clusterName: clusterMap[item.cluster_id].clusterName,
              clusterType: clusterMap[item.cluster_id].clusterType,
              sepc: {
                id: slaveItem.spec_id,
                name: specInfo ? specInfo.spec_name : '',
              },
            };
            results.push(obj);
          });
        }

        return results;
      }, [] as RowData[]);
    },
  });

</script>
