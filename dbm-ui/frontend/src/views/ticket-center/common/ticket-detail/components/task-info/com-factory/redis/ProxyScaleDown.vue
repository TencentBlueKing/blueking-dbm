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

  import RedisModel from '@services/model/redis/redis';
  // import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import type { RedisProxyScaleDownDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';
  // import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { getRedisListByBizId } from '@services/source/redis';

  interface Props {
    ticketDetails: TicketModel<RedisProxyScaleDownDetails>
  }

  interface RowData {
    clusterName: string,
    clusterType: string,
    nodeType: string,
    spec: {
      // id: number,
      name: string,
      count: number,
    }[],
    hostSelectType: string,
    targetNum: number,
    switchMode: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);
  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('架构版本'),
      field: 'clusterTypeName',
      showOverflowTooltip: true,
    },
    {
      label: t('缩容节点类型'),
      field: 'nodeType',
    },
    // {
    //   label: t('当前规格'),
    //   field: 'sepc',
    //   showOverflowTooltip: true,
    //   render: ({ data }: {data: RowData}) => data.spec.map(specItem => (
    //     <div style="line-height: 26px">
    //       <span>{ specItem.name }</span>
    //       <span class="ml-4">({specItem.count}{t('台')}) </span>
    //     </div>
    //   )),
    // },
    {
      label: t('主机选择方式'),
      field: 'hostSelectType',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => (
        <div style="white-space: break-spaces; line-height: 18px">{data.hostSelectType}</div>
      )
    },
    {
      label: t('缩容数量(台)'),
      field: 'targetNum',
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  const { loading } = useRequest(getRedisListByBizId, {
    defaultParams: [{
      bk_biz_id: props.ticketDetails.bk_biz_id,
      offset: 0,
      limit: -1,
    }],
    onSuccess: async (result) => {
      if (result.results.length < 1) {
        return;
      }

      const clusterMap = result.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: {
          clusterName: item.master_domain,
          clusterType: item.cluster_spec.spec_cluster_type,
          proxyList: item.proxy
        } });
        return obj;
      }, {} as Record<number, {clusterName: string, clusterType: string, proxyList: RedisModel['proxy']}>);

      tableData.value = infos.map((item) => {
        const proxySpecMap = clusterMap[item.cluster_id].proxyList
          .map(proxyItem => proxyItem.spec_config)
          .reduce<Record<number, RedisModel['proxy'][number]['spec_config'] & { count: number }>>(
            (prevSpecMap, dataItem) => {
              const specId = dataItem.id;
              if (prevSpecMap[specId]) {
                Object.assign(prevSpecMap[specId], {
                  ...prevSpecMap[specId],
                  count: prevSpecMap[specId].count + 1,
                });
                return prevSpecMap;
              }
              return Object.assign(prevSpecMap, {
                [specId]: {
                  ...dataItem,
                  count: 1,
                },
              });
            },
            {},
          );
        const spec = Object.values(proxySpecMap).map((specItem) => ({
          name: specItem.name,
          count: specItem.count
        }));
        const ipList = (item.proxy_reduced_hosts || []).map(item => item.ip)
        return {
          clusterName: clusterMap[item.cluster_id].clusterName,
          clusterType: clusterMap[item.cluster_id].clusterType,
          clusterTypeName: clusters[item.cluster_id].cluster_type_name,
          nodeType: 'Proxy',
          spec,
          hostSelectType: ipList.length > 0 ? ipList.join('\n') : t('自动匹配'),
          targetNum: clusterMap[item.cluster_id].proxyList.length - (item.target_proxy_count || ipList.length),
          switchMode: item.online_switch_type,
        };
      });
    }
  })

  // const { loading } = useRequest(getRedisListByBizId, {
  //   defaultParams: [{
  //     bk_biz_id: props.ticketDetails.bk_biz_id,
  //     offset: 0,
  //     limit: -1,
  //   }],
  //   onSuccess: async (result) => {
  //     if (result.results.length < 1) {
  //       return;
  //     }
  //     const clusterMap = result.results.reduce((obj, item) => {
  //       Object.assign(obj, { [item.id]: {
  //         clusterName: item.master_domain,
  //         clusterType: item.cluster_spec.spec_cluster_type,
  //         specId: item.cluster_spec.spec_id,
  //         proxyCount: item.proxy.length
  //       } });
  //       return obj;
  //     }, {} as Record<number, {clusterName: string, clusterType: string, specId: number, proxyCount: number}>);

  //     // 避免重复查询
  //     const clusterTypes = [...new Set(Object.values(clusterMap).map(item => item.clusterType))];
  //     const sepcMap: Record<string, ResourceSpecModel[]> = {};

  //     await Promise.all(clusterTypes.map(async (type) => {
  //       const ret = await getResourceSpecList({
  //         spec_cluster_type: type,
  //         limit: -1,
  //         offset: 0,
  //       });
  //       sepcMap[type] = ret.results;
  //     }));
  //     loading.value = false;
  //     tableData.value = infos.map((item) => {
  //       const sepcList = sepcMap[clusterMap[item.cluster_id].clusterType];
  //       const specInfo = sepcList.find(row => row.spec_id === clusterMap[item.cluster_id].specId);
  //       const ipList = (item.proxy_reduced_hosts || []).map(item => item.ip)
  //       return {
  //         clusterName: clusterMap[item.cluster_id].clusterName,
  //         clusterType: clusterMap[item.cluster_id].clusterType,
  //         clusterTypeName: clusters[item.cluster_id].cluster_type_name,
  //         nodeType: 'Proxy',
  //         sepc: {
  //           id: clusterMap[item.cluster_id].specId,
  //           name: specInfo ? specInfo.spec_name : '',
  //         },
  //         hostSelectType: ipList.length > 0 ? ipList.join('\n') : t('自动匹配'),
  //         targetNum: clusterMap[item.cluster_id].proxyCount - (item.target_proxy_count || ipList.length),
  //         switchMode: item.online_switch_type,
  //       };
  //     });
  //   },
  // });
</script>
