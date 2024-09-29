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
    <BkTable
      :data="tableData"
      show-overflow-tooltip>
      <BkTableColumn
        field="master_domain"
        :label="t('目标集群')">
      </BkTableColumn>
      <BkTableColumn
        field="cluster_type_name"
        :label="t('架构版本')">
      </BkTableColumn>
      <BkTableColumn
        field="db_version"
        :label="t('Redis版本')">
      </BkTableColumn>
      <BkTableColumn
        :label="t('当前容量')"
        :min-width="240">
        <template #default="{ data }: { data: RowData }">
          <TableGroupContent
            v-if="data"
            :columns="getCurrentColunms(data)" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('目标容量')"
        :min-width="370">
        <template #default="{ data }: { data: RowData }">
          <TableGroupContent
            v-if="data"
            :columns="getTargetColunms(data)" />
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('切换模式')">
        <template #default="{ data }: { data: RowData }">
          {{ data.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
        </template>
      </BkTableColumn>
    </BkTable>
  </BkLoading>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import type { RedisScaleUpDownDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue'

  import { convertStorageUnits } from '@utils';

  import TableGroupContent from '../components/TableGroupContent.vue'

  interface Props {
    ticketDetails: TicketModel<RedisScaleUpDownDetails>
  }

  type RowData = RedisModel & RedisScaleUpDownDetails['infos'][number]

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const { infos, specs } = props.ticketDetails.details;

  const { loading } = useRequest(getRedisList, {
    defaultParams: [{
      cluster_ids: infos.map((item) => item.cluster_id).join(','),
    }],
    onSuccess(clustersResult) {
      const clusterInfo = clustersResult.results.reduce<Record<number, RedisModel>>((results, item) => {
        Object.assign(results, {
          [item.id]: item,
        });
        return results;
      }, {})
      tableData.value = infos.map((infoItem) =>
        Object.assign(
          {},
          clusterInfo[infoItem.cluster_id],
          infoItem,
        ));
    }
  })

  const getCurrentColunms = (data: RowData) => [
    {
      title: t('当前容量'),
      render: () => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      title: t('资源规格'),
      render: () => {
        const currentSpec = {
          ...data.cluster_spec,
          id: data.cluster_spec.spec_id,
          name: data.cluster_spec.spec_name,
        }
        return (
          <RenderSpec
            data={currentSpec}
            hide-qps={!currentSpec.qps.max}
            is-ignore-counts />
        )
      }
    },
    {
      title: t('机器组数'),
      render: () => data.machine_pair_cnt
    },
    {
      title: t('机器数量'),
      render: () => data.machine_pair_cnt * 2
    },
    {
      title: t('分片数'),
      render: () => data.cluster_shard_num
    },
  ]

  const getTargetColunms = (data: RowData) => [
    {
      title: t('目标容量'),
      render: () => {
        const { used = 0, total = 0 } = data.cluster_stats;
        const targetTotal = convertStorageUnits(data.future_capacity, 'GB', 'B')
        const currentValue = data.cluster_capacity || convertStorageUnits(total, 'B', 'GB')

        let stats = {}
        if (!_.isEmpty(data.cluster_stats)) {
          stats = {
            used,
            total: targetTotal,
            in_use: Number((used / targetTotal * 100).toFixed(2))
          }
        }

        return (
          <>
            <ClusterCapacityUsageRate clusterStats={stats} />
            <ValueDiff
              currentValue={currentValue}
              num-unit="G"
              targetValue={data.future_capacity} />
          </>
        )
      }
    },
    {
      title: t('资源规格'),
      render: () => {
        const targetSpec = specs[data.resource_spec.backend_group.spec_id]
        return (
          <RenderSpec
            data={targetSpec}
            hide-qps={!targetSpec.qps.max}
            is-ignore-counts />
        )
      }
    },
    {
      title: t('机器组数'),
      render: () => {
        const targetValue = data.group_num
        return (
          <>
            <span>{targetValue}</span>
            <ValueDiff
              currentValue={data.machine_pair_cnt}
              show-rate={false}
              targetValue={targetValue} />
          </>
        )
      }
    },
    {
      title: t('机器数量'),
      render: () => {
        const targetValue = data.group_num * 2
        return (
          <>
            <span>{targetValue}</span>
            <ValueDiff
              currentValue={data.machine_pair_cnt * 2}
              show-rate={false}
              targetValue={targetValue} />
          </>
        )
      }
    },
    {
      title: t('分片数'),
      render: () => (
        <>
          <span>{data.shard_num}</span>
          <ValueDiff
            currentValue={data.cluster_shard_num}
            show-rate={false}
            targetValue={data.shard_num} />
        </>
      )
    },
    {
      title: t('变更方式'),
      render: () => {
        if (data.update_mode) {
          return data.update_mode === 'keep_current_machines' ? t('原地变更') : t('替换变更')
        }
        return '--'
      }
    }
  ]
</script>

<style lang="less" scoped>
  :deep(.render-spec-box) {
    height: auto;
    padding: 0;
  }
</style>
