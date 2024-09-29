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
    :columns="columns"
    :data="tableData" />
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('数据校验') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails.details.need_checksum ? t('是') : t('否') }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('校验时间') }}：</span>
      <span class="ticket-details-item-value">
        {{ isTimer ? t('定时执行') : t('立即执行') }}
      </span>
    </div>
    <div
      v-if="isTimer"
      class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('定时执行时间') }}：</span>
      <span class="ticket-details-item-value">
        {{ utcDisplayTime(ticketDetails.details.trigger_checksum_time) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import type { SpiderNodeRebalanceDetails } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { getTendbclusterListByBizId } from '@services/source/tendbcluster';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<SpiderNodeRebalanceDetails>
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
    prev_machine_pair: number
    prev_cluster_spec_name: string
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const isTimer = props.ticketDetails.details.trigger_checksum_type === 'timer';
  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('集群分片数'),
      field: 'shardNum',
    },
    {
      label: t('当前机器组数'),
      field: 'prev_machine_pair',
    },
    {
      label: t('当前资源规格'),
      field: 'prev_cluster_spec_name',
    },
    {
      label: t('目标机器组数'),
      field: 'groupNum',
    },
    {
      label: t('目标资源规格'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
  ];

  useRequest(getTendbclusterListByBizId, {
    defaultParams: [{
      bk_biz_id: props.ticketDetails.bk_biz_id,
      offset: 0,
      limit: -1,
    }],
    onSuccess: async (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce<Record<number, {clusterName: string, clusterType: string}>>((obj, item) => {
        Object.assign(obj, { [item.id]: {
          clusterName: item.master_domain,
          clusterType: item.cluster_spec.spec_cluster_type,
        } });
        return obj;
      }, {});

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
      tableData.value = infos.map((item) => {
        const sepcList = sepcMap[clusterMap[item.cluster_id].clusterType];
        const specInfo = sepcList.find(row => row.spec_id === item.resource_spec.backend_group.spec_id);
        return {
          clusterName: clusterMap[item.cluster_id].clusterName,
          clusterType: clusterMap[item.cluster_id].clusterType,
          shardNum: item.cluster_shard_num,
          groupNum: item.resource_spec.backend_group.count,
          sepc: {
            id: item.resource_spec.backend_group.spec_id,
            name: specInfo ? specInfo.spec_name : '',
          },
          prev_machine_pair: item.prev_machine_pair,
          prev_cluster_spec_name: item.prev_cluster_spec_name
        };
      });
    },
  });
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
