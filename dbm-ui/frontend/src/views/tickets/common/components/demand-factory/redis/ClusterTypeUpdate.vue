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
  <div class="ticket-details__info">
    <div
      class="ticket-details__item"
      style="align-items: flex-start;">
      <span
        class="ticket-details__item-label">{{ t('变更信息') }}：</span>
      <span class="ticket-details__item-value">
        <BkLoading :loading="loading">
          <DbOriginalTable
            :columns="columns"
            :data="tableData" />
        </BkLoading>
      </span>
    </div>
  </div>

  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('校验与修复类型') }}：</span>
        <span class="ticket-details__item-value">
          {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
        </span>
      </div>
      <div
        v-if="ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'"
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('校验与修复频率设置') }}：</span>
        <span class="ticket-details__item-value">
          {{ repairAndVerifyFrequencyMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { listClusterList } from '@services/redis/toolbox';
  import { getResourceSpecList } from '@services/resourceSpec';
  import type { RedisClusterTypeUpdateDetails, TicketDetails } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/redis/common/const';

  interface Props {
    ticketDetails: TicketDetails<RedisClusterTypeUpdateDetails>
  }

  interface RowData {
    clusterName: string,
    currentSepc: string,
    srcClusterType: string,
    targetClusterType: string,
    deployPlan: string,
    dbVersion: string,
    switchMode: string,
    capacity: number,
    futureCapacity: number,
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('源集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('原集群类型'),
      field: 'srcClusterType',
      showOverflowTooltip: true,
    },
    {
      label: t('目标集群类型'),
      field: 'targetClusterType',
      showOverflowTooltip: true,
    },
    {
      label: t('当前集群容量/QPS'),
      field: 'currentSepc',
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
      label: t('部署方案'),
      field: 'deployPlan',
      showOverflowTooltip: true,
    },
    {
      label: t('版本'),
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

  const repairAndVerifyTypesMap = generateMap(repairAndVerifyTypeList);

  const repairAndVerifyFrequencyMap = generateMap(repairAndVerifyFrequencyList);

  const clusterTypeMap: Record<string, string> = {
    [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: t('TendisCache'),
    [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: t('TendisSSD'),
    [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: t('Tendisplus'),
  };

  const { loading } = useRequest(listClusterList, {
    defaultParams: [currentBizId],
    onSuccess: async (r) => {
      if (r.length < 1) {
        return;
      }
      const clusterMap = r.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item });
        return obj;
      }, {} as Record<string, RedisModel>);

      // 避免重复查询
      const clusterTypes = [...new Set(infos.map(item => item.target_cluster_type))];
      const sepcMap: Record<string, ResourceSpecModel[]> = {};

      await Promise.all(clusterTypes.map(async (type) => {
        const ret = await getResourceSpecList({
          spec_cluster_type: type,
        });
        sepcMap[type] = ret.results;
      }));
      loading.value = false;
      tableData.value = infos.map((item) => {
        const currentCluster = clusterMap[item.src_cluster];
        const specConfig = currentCluster.cluster_spec;
        // eslint-disable-next-line max-len
        const targetSepcPlan =  sepcMap[item.target_cluster_type].filter(row => row.spec_id === item.resource_spec.backend_group.spec_id);
        return ({
          clusterName: currentCluster.master_domain,
          srcClusterType: clusterTypeMap[currentCluster.cluster_spec.spec_cluster_type],
          currentSepc: `${currentCluster.cluster_capacity}G_${specConfig.qps.max}/s（${item.current_shard_num} 分片）`,
          deployPlan: targetSepcPlan.length > 0 ? targetSepcPlan[0].spec_name : '',
          targetClusterType: clusterTypeMap[item.target_cluster_type],
          dbVersion: item.db_version,
          switchMode: item.online_switch_type,
          capacity: item.capacity,
          futureCapacity: item.future_capacity,
        });
      });
    },
  });

  // 生成映射表
  function generateMap(arr: { label: string, value: string}[]) {
    return arr.reduce((obj, item) => {
      Object.assign(obj, { [item.value]: item.label });
      return obj;
    }, {} as Record<string, string>);
  }


</script>
<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
