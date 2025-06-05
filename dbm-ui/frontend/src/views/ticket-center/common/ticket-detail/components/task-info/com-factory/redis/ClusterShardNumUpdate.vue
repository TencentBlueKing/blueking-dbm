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
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :width="150">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="db_version"
      :label="t('Redis 版本')" />
    <BkTableColumn
      :label="t('当前方案')"
      :min-width="400">
      <template #default="{ data }: { data: RowData }">
        <TableGroupContent
          v-if="data"
          :columns="getCurrentColunms(data)"
          :title-width="90" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('新部署方案')"
      :min-width="400">
      <template #default="{ data }: { data: RowData }">
        <TableGroupContent
          v-if="data"
          :columns="getTargetColunms(data)"
          :title-width="90" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('切换模式')"
      :width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('校验与修复类型')">
      {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'"
      :label="t('校验与修复频率设置')">
      {{ repairAndVerifyFrequencyMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';
  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/db-manage/redis/common/const';

  import { convertStorageUnits } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';
  import TableGroupContent from '../components/TableGroupContent.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterShardNumUpdate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  // 生成映射表
  const generateMap = (arr: { label: string; value: string }[]) => {
    return arr.reduce<Record<string, string>>((obj, item) => {
      Object.assign(obj, { [item.value]: item.label });
      return obj;
    }, {});
  };

  const repairAndVerifyTypesMap = generateMap(repairAndVerifyTypeList);
  const repairAndVerifyFrequencyMap = generateMap(repairAndVerifyFrequencyList);

  const getCurrentColunms = (data: RowData) => [
    {
      render: () => {
        if (data.proxy) {
          const targetSpec = data.proxy[0].spec_config;
          return (
            <RenderSpec
              data={targetSpec}
              hide-qps={!targetSpec.qps.max}
              is-ignore-counts
            />
          );
        }
        return '--';
      },
      title: t('Proxy 规格'),
    },
    {
      render: () => {
        if (data.proxy) {
          return <span style='font-weight: bolder'>{data.proxy.length}</span>;
        }
        return '--';
      },
      title: t('Proxy 数量'),
    },
    {
      render: () => {
        if (data.cluster_stats) {
          return <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />;
        }
        return '--';
      },
      title: t('使用率'),
    },
    {
      render: () => {
        if (data.cluster_spec) {
          const targetSpec = { ...data.cluster_spec, name: data.cluster_spec.spec_name };
          return (
            <RenderSpec
              data={targetSpec}
              hide-qps={!targetSpec.qps.max}
              is-ignore-counts
            />
          );
        }
        return '--';
      },
      title: t('后端存储规格'),
    },
    {
      render: () => {
        if (data.machine_pair_cnt) {
          return <span style='font-weight: bolder'>{data.machine_pair_cnt || '--'}</span>;
        }
        return '--';
      },
      title: t('机器组数'),
    },
    {
      render: () => {
        if (data.machine_pair_cnt) {
          return <span style='font-weight: bolder'>{data.machine_pair_cnt * 2 || '--'}</span>;
        }
        return '--';
      },
      title: t('机器数量'),
    },
    {
      render: () => <span style='font-weight: bolder'>{data.current_shard_num || '--'}</span>,
      title: t('分片数'),
    },
  ];

  const getTargetColunms = (data: RowData) => [
    {
      render: () => {
        const targetSpec = props.ticketDetails.details.specs[data.resource_spec.proxy.spec_id];
        return (
          <RenderSpec
            data={targetSpec}
            hide-qps={!targetSpec.qps.max}
            is-ignore-counts
          />
        );
      },
      title: t('Proxy 规格'),
    },
    {
      render: () => (
        <>
          <span style='font-weight: bolder'>{data.resource_spec.proxy.count}</span>
          <ValueDiff
            v-if={data.proxy}
            currentValue={data.proxy?.length ?? 0}
            showRate={false}
            targetValue={data.resource_spec.proxy.count}
          />
        </>
      ),
      title: t('Proxy 数量'),
    },
    {
      render: () => {
        if (_.isEmpty(data.cluster_stats)) {
          return '--';
        }
        const { used = 0 } = data.cluster_stats;
        const targetTotal = convertStorageUnits(data.future_capacity ?? 0, 'GB', 'B');

        const stats = {
          in_use: Number(((used / targetTotal) * 100).toFixed(2)),
          total: targetTotal,
          used,
        };
        return (
          <>
            <ClusterCapacityUsageRate clusterStats={stats} />
            <ValueDiff
              currentValue={convertStorageUnits(data.cluster_stats.total, 'B', 'GB')}
              num-unit='G'
              targetValue={data.future_capacity}
            />
          </>
        );
      },
      title: t('使用率'),
    },
    {
      render: () => {
        const targetSpec = props.ticketDetails.details.specs[data.resource_spec.backend_group.spec_id];
        return (
          <RenderSpec
            data={targetSpec}
            hide-qps={!targetSpec.qps.max}
            is-ignore-counts
          />
        );
      },
      title: t('后端存储规格'),
    },
    {
      render: () => (
        <>
          <span style='font-weight: bolder'>{data.resource_spec.backend_group.count}</span>
          <ValueDiff
            v-if={data.machine_pair_cnt}
            currentValue={data?.machine_pair_cnt ?? 0}
            showRate={false}
            targetValue={data.resource_spec.backend_group.count}
          />
        </>
      ),
      title: t('机器组数'),
    },
    {
      render: () => (
        <>
          <span style='font-weight: bolder'>{data.resource_spec.backend_group.count * 2}</span>
          <ValueDiff
            v-if={data.machine_pair_cnt}
            currentValue={(data?.machine_pair_cnt ?? 0) * 2}
            showRate={false}
            targetValue={data.resource_spec.backend_group.count * 2}
          />
        </>
      ),
      title: t('机器数量'),
    },
    {
      render: () => (
        <>
          <span style='font-weight: bolder'>{data.cluster_shard_num}</span>
          <ValueDiff
            currentValue={data.current_shard_num}
            showRate={false}
            targetValue={data.cluster_shard_num}
          />
        </>
      ),
      title: t('分片数'),
    },
  ];
</script>
<style lang="less" scoped>
  :deep(.render-spec-box) {
    height: auto;
    padding: 0;
  }
</style>
