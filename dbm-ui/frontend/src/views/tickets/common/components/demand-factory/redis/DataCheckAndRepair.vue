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
    :data="ticketDetails.details.infos" />
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('执行模式') }}：</span>
        <span class="ticket-details__item-value">{{ executeModesMap[ticketDetails.details.execute_mode] }}</span>
      </div>
      <div
        v-if="ticketDetails.details.execute_mode === 'scheduled_execution'"
        class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('指定执行时间') }}：</span>
        <span class="ticket-details__item-value">{{ ticketDetails.details.specified_execution_time }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('指定停止时间') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.check_stop_time }}
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('一直保持校验修复') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.keep_check_and_repair ? t('是') : t('否') }}
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('修复数据') }}：</span>
        <span class="ticket-details__item-value">
          {{ ticketDetails.details.data_repair_enabled ? t('是') : t('否') }}
        </span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('修复模式') }}：</span>
        <span class="ticket-details__item-value">
          {{ repairModesMap[ticketDetails.details.repair_mode] }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { RedisDataCheckAndRepairDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<RedisDataCheckAndRepairDetails>
  }

  type RowData = RedisDataCheckAndRepairDetails['infos'][0];

  defineProps<Props>();

  const { t } = useI18n();

  const executeModesMap = {
    auto_execution: t('自动执行'),
    scheduled_execution: t('定时执行'),
  };

  const repairModesMap = {
    auto_repair: t('自动修复'),
    manual_confirm: t('人工确认'),
  };

  const columns = [
    {
      label: t('关联单据'),
      field: 'bill_id',
    },
    {
      label: t('源集群'),
      field: 'src_cluster',
      showOverflowTooltip: true,
    },
    {
      label: t('源实例'),
      field: 'src_instances',
      showOverflowTooltip: true,
    },
    {
      label: t('目标集群'),
      field: 'taregtClusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('包含 Key'),
      field: 'targetNum',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => {
        if (data.key_white_regex.length > 0) {
          return data.key_white_regex.split('\n').map((key, index) => <bk-tag key={index} type="stroke">{key}</bk-tag>);
        }
        return <span>--</span>;
      },
    },
    {
      label: t('排除 Key'),
      field: 'time',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => {
        if (data.key_black_regex.length > 0) {
          return data.key_black_regex.split('\n').map((key, index) => <bk-tag key={index} type="stroke">{key}</bk-tag>);
        }
        return <span>--</span>;
      },
    },
  ];


</script>
<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
