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

  import type { TicketDetails } from '@services/types/ticket';

  import type { DetailClusters } from '../common/types';

  // redis 数据校验与修复
  export interface RedisDataCheckAndRepairDetails {
    clusters: DetailClusters;
    /**
     * execute_mode 执行模式
     * - auto_execution 自动执行
     * - scheduled_execution 定时执行
     */
    execute_mode: 'auto_execution' | 'scheduled_execution';
    specified_execution_time: string; // 定时执行,指定执行时间
    check_stop_time: string; // 校验终止时间,
    keep_check_and_repair: boolean; // 是否一直保持校验
    data_repair_enabled: boolean; // 是否修复数据
    repair_mode: 'auto_repair' | 'manual_confirm';
    infos: [
      {
        bill_id: number; // 关联的(数据复制)单据ID
        src_cluster: string; // 源集群,来自于数据复制记录
        src_instances: string[]; // 源实例列表
        dst_cluster: string; // 目的集群,来自于数据复制记录
        key_white_regex: string; // 包含key
        key_black_regex: string; // 排除key
      },
    ];
  }

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
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
