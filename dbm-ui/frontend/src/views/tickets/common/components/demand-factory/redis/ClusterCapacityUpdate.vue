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
  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { getRedisList } from '@services/source/redis';
  import type { RedisScaleUpDownDetails, TicketDetails } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  interface Props {
    ticketDetails: TicketDetails<RedisScaleUpDownDetails>
  }

  interface RowData {
    clusterName: string,
    clusterType: string,
    sepc: {
      id: number,
      name: string,
    },
    shardNum: number,
    groupNum: number,
    capacity: number,
    futureCapacity: number,
    dbVersion: string,
    switchMode: string,
  }


  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('集群分片数'),
      field: 'shardNum',
      showOverflowTooltip: true,
    },
    {
      label: t('部署机器组数'),
      field: 'groupNum',
      showOverflowTooltip: true,
    },
    {
      label: t('当前容量需求'),
      field: 'capacity',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.capacity}G</span>,
    },
    {
      label: t('未来容量需求'),
      field: 'futureCapacity',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.futureCapacity}G</span>,
    },
    {
      label: t('目标资源规格'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
    {
      label: t('指定Redis版本'),
      field: 'dbVersion',
      showOverflowTooltip: true,
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  const { loading } = useRequest(getRedisList, {
    defaultParams: [{ bk_biz_id: currentBizId }],
    onSuccess: async (result) => {
      if (result.results.length < 1) {
        return;
      }
      const clusterMap = result.results.reduce((obj, item) => {
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
      tableData.value = infos.map((item) => {
        const sepcList = sepcMap[clusterMap[item.cluster_id].clusterType];
        const specInfo = sepcList.find(row => row.spec_id === item.resource_spec.backend_group.spec_id);
        return {
          clusterName: clusterMap[item.cluster_id].clusterName,
          clusterType: clusterMap[item.cluster_id].clusterType,
          shardNum: item.shard_num,
          groupNum: item.group_num,
          dbVersion: item.db_version,
          capacity: item.capacity,
          futureCapacity: item.future_capacity,
          sepc: {
            id: item.resource_spec.backend_group.spec_id,
            name: specInfo ? specInfo.spec_name : '',
          },
          switchMode: item.online_switch_type,
        };
      });
    },
  });

</script>
