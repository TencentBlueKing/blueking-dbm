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
    <InfoItem :label="t('数据校验:')">
      {{ ticketDetails.details.need_checksum ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('校验时间:')">
      {{ isTimer ? t('定时执行') : t('立即执行') }}
    </InfoItem>
    <InfoItem
      v-if="isTimer"
      :label="t('定时执行时间:')">
      {{ utcDisplayTime(ticketDetails.details.trigger_checksum_time) }}
    </InfoItem>
  </InfoList>
  <BkLoading :loading="loading">
    <BkTable :data="tableData">
      <BkTableColumn :label="t('目标集群')">
        <template #default="{ data }: { data: RowData }">
          {{ data.clusterName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('当前资源规格')">
        <template #default="{ data }: { data: RowData }">
          {{ data.prev_cluster_spec_name }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('集群分片数')">
        <template #default="{ data }: { data: RowData }">
          {{ data.shardNum }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('部署机器组数')">
        <template #default="{ data }: { data: RowData }">
          {{ data?.groupNum }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('当前总容量')">
        <template #default="{ data }: { data: RowData }">
          {{ data.prev_cluster_spec_name }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('目标总容量')">
        <template #default="{ data }: { data: RowData }">
          {{ data.sepcName }}
        </template>
      </BkTableColumn>
    </BkTable>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { getSpiderListByBizId } from '@services/source/spider';

  import { TicketTypes } from '@common/const';

  import InfoList, {
    Item as InfoItem,
  } from '@views/tickets/common/components/demand-factory/components/info-list/Index.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.NodeRebalance>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_NODE_REBALANCE,
  });

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;
  const isTimer = props.ticketDetails.details.trigger_checksum_type === 'timer';

  interface RowData {
    clusterName: string;
    clusterType: string;
    sepcName: string;
    shardNum: number;
    groupNum: number;
    prev_machine_pair: number;
    prev_cluster_spec_name: string;
  }
  const tableData = ref<RowData[]>([]);

  const { loading } = useRequest(getSpiderListByBizId, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        offset: 0,
        limit: -1,
      },
    ],
    onSuccess: async (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce(
        (obj, item) => {
          Object.assign(obj, {
            [item.id]: {
              clusterName: item.master_domain,
              clusterType: item.cluster_spec.spec_cluster_type,
            },
          });
          return obj;
        },
        {} as Record<number, { clusterName: string; clusterType: string }>,
      );

      // 避免重复查询
      const clusterTypes = [...new Set(Object.values(clusterMap).map((item) => item.clusterType))];
      const sepcMap: Record<string, ResourceSpecModel[]> = {};
      await Promise.all(
        clusterTypes.map(async (type) => {
          const ret = await getResourceSpecList({
            spec_cluster_type: type,
            limit: -1,
            offset: 0,
          });
          sepcMap[type] = ret.results;
        }),
      );
      loading.value = false;
      tableData.value = infos.map((item) => {
        const sepcList = sepcMap[clusterMap[item.cluster_id].clusterType];
        const specInfo = sepcList.find((row) => row.spec_id === item.resource_spec.backend_group.spec_id);
        return {
          clusterName: clusterMap[item.cluster_id].clusterName,
          clusterType: clusterMap[item.cluster_id].clusterType,
          shardNum: item.cluster_shard_num,
          groupNum: item.resource_spec.backend_group.count,
          sepcName: specInfo ? specInfo.spec_name : '',
          prev_machine_pair: item.prev_machine_pair,
          prev_cluster_spec_name: item.prev_cluster_spec_name,
        };
      });
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
