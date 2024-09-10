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
    <BkTable :data="tableData">
      <BkTableColumn :label="t('目标集群')">
        <template #default="{ data }: { data: RowData }">
          {{ data.clusterName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('规格')">
        <template #default="{ data }: { data: RowData }">
          {{ data.sepcName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('部署台数')">
        <template #default="{ data }: { data: RowData }">
          {{ data.targetNum }}
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

  interface Props {
    ticketDetails: TicketModel<TendbCluster.SpiderSlaveApply>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY,
  });

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;
  interface RowData {
    clusterName: string;
    sepcName: string;
    targetNum: number;
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
        const specInfo = sepcList.find((row) => row.spec_id === item.resource_spec.spider_slave_ip_list.spec_id);
        return {
          clusterName: clusterMap[item.cluster_id].clusterName,
          sepcName: specInfo ? specInfo.spec_name : '',
          targetNum: item.resource_spec.spider_slave_ip_list.count,
        };
      });
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
