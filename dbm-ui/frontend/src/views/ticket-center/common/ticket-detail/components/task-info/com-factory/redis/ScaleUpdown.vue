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
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      fixed="left"
      :label="t('源集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="db_version"
      :label="t('Redis版本')"
      :min-width="100">
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
    <BkTableColumn
      :label="t('切换模式')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        {{ data.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue'

  import { convertStorageUnits } from '@utils';

  import TableGroupContent from '../components/TableGroupContent.vue'

  interface Props {
    ticketDetails: TicketModel<Redis.ScaleUpdown>
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_SCALE_UPDOWN,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const getCurrentColunms = (data: RowData) => [
    {
      title: t('当前容量'),
      render: () => {
        if (_.isEmpty(data.display_info?.cluster_stats)) {
          return '--'
        }
        return <ClusterCapacityUsageRate clusterStats={data.display_info.cluster_stats} />
      }
    },
    {
      title: t('资源规格'),
      render: () => {
        if (_.isEmpty(data.display_info?.cluster_spec)) {
          return '--'
        }
        const currentSpec = {
          ...data.display_info.cluster_spec,
          id: data.display_info.cluster_spec.spec_id,
          name: data.display_info.cluster_spec.spec_name,
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
      render: () => data.display_info?.machine_pair_cnt || '--'
    },
    {
      title: t('机器数量'),
      render: () => data.display_info?.machine_pair_cnt ? data.display_info.machine_pair_cnt * 2 : '--'
    },
    {
      title: t('分片数'),
      render: () => data.display_info?.cluster_shard_num || '--'
    },
  ]

  const getTargetColunms = (data: RowData) => [
    {
      title: t('目标容量'),
      render: () => {
        if (_.isEmpty(data.display_info?.cluster_stats)) {
          return '--'
        }
        const { used = 0, total = 0 } = data.display_info.cluster_stats;
        const targetTotal = convertStorageUnits(data.future_capacity, 'GB', 'B')
        const currentValue = data.display_info.cluster_capacity || convertStorageUnits(total, 'B', 'GB')
        const stats = {
          used,
          total: targetTotal,
          in_use: Number((used / targetTotal * 100).toFixed(2))
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
        const targetSpec = props.ticketDetails.details.specs[data.resource_spec.backend_group.spec_id]
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
      render: () => data.group_num
    },
    {
      title: t('机器数量'),
      render: () => data.group_num * 2
    },
    {
      title: t('分片数'),
      render: () => data.shard_num
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
