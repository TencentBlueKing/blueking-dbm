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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TableColumn
      fixed="left"
      :min-width="250"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="180"
      :title="t('架构版本')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="db_version"
      :min-width="100"
      :title="t('Redis版本')">
    </TableColumn>
    <TableColumn
      :min-width="240"
      :title="t('当前容量')">
      <template #default="{ row }: { row: RowData }">
        <TableGroupContent
          v-if="row"
          :columns="getCurrentColunms(row)" />
      </template>
    </TableColumn>
    <TableColumn
      :min-width="370"
      :title="t('目标容量')">
      <template #default="{ row }: { row: RowData }">
        <TableGroupContent
          v-if="row"
          :columns="getTargetColunms(row)" />
      </template>
    </TableColumn>
    <TableColumn
      :min-width="120"
      :title="t('切换模式')">
      <template #default="{ row }: { row: RowData }">
        {{ row.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import RenderSpec from '@components/spec-display/Index.vue';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  import TableGroupContent from '../components/TableGroupContent.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ScaleUpdown>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_SCALE_UPDOWN,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const getCurrentColunms = (data: RowData) => [
    {
      render: () => (data.display_info?.cluster_capacity ? `${data.display_info.cluster_capacity} G` : '--'),
      title: t('容量'),
    },
    {
      render: () => {
        if (_.isEmpty(data.display_info?.cluster_spec)) {
          return '--';
        }
        const currentSpec = {
          ...data.display_info.cluster_spec,
          id: data.display_info.cluster_spec.spec_id,
          name: data.display_info.cluster_spec.spec_name,
        };
        return (
          <RenderSpec
            data={currentSpec}
            hide-qps={!currentSpec.qps.max}
            is-ignore-counts
          />
        );
      },
      title: t('资源规格'),
    },
    {
      render: () => data.display_info?.machine_pair_cnt || '--',
      title: t('机器组数'),
    },
    {
      render: () => (data.display_info?.machine_pair_cnt ? data.display_info.machine_pair_cnt * 2 : '--'),
      title: t('机器数量'),
    },
    {
      render: () => data.display_info?.cluster_shard_num || '--',
      title: t('集群分片数'),
    },
  ];

  const getTargetColunms = (data: RowData) => [
    {
      render: () => {
        if (!data.future_capacity) {
          return '--';
        }
        return (
          <>
            {`${data.future_capacity} G`}
            <ValueDiff
              currentValue={data.display_info.cluster_capacity}
              num-unit='G'
              targetValue={data.future_capacity}
            />
          </>
        );
      },
      title: t('容量'),
    },
    {
      render: () => {
        const targetSpec = props.ticketDetails.details.specs[data.resource_spec.backend_group.spec_id];
        return (
          <RenderSpec
            data={targetSpec}
            is-ignore-counts
          />
        );
      },
      title: t('资源规格'),
    },
    {
      render: () => {
        if (!data.group_num) {
          return '--';
        }
        return (
          <>
            {data.group_num}
            <ValueDiff
              currentValue={data.display_info.machine_pair_cnt}
              show-rate={false}
              targetValue={data.group_num}
            />
          </>
        );
      },
      title: t('机器组数'),
    },
    {
      render: () => {
        if (!data.group_num) {
          return '--';
        }
        return (
          <>
            {data.group_num * 2}
            <ValueDiff
              currentValue={data.display_info.machine_pair_cnt * 2}
              show-rate={false}
              targetValue={data.group_num * 2}
            />
          </>
        );
      },
      title: t('机器数量'),
    },
    {
      render: () => {
        if (!data.shard_num) {
          return '--';
        }
        return (
          <>
            {data.shard_num}
            <ValueDiff
              currentValue={data.display_info?.cluster_shard_num || 0}
              show-rate={false}
              targetValue={data.shard_num}
            />
          </>
        );
      },
      title: t('集群分片数'),
    },
    {
      render: () => {
        if (data.update_mode) {
          return data.update_mode === 'keep_current_machines' ? t('原地变更') : t('替换变更');
        }
        return '--';
      },
      title: t('变更方式'),
    },
  ];
</script>

<style lang="less" scoped>
  :deep(.render-spec-box) {
    height: auto;
    padding: 0;
  }
</style>
