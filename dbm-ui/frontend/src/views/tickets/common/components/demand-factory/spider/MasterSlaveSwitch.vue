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
      <span class="ticket-details-item-label">{{ t('检查业务来源的连接') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails.details.is_check_process ? t('是') : t('否') }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('检查主从同步延迟') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails.details.is_check_delay ? t('是') : t('否') }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('检查主从数据校验结果') }}：</span>
      <span class="ticket-details-item-value">
        {{ ticketDetails.details.is_verify_checksum ? t('是') : t('否') }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { SpiderMasterSlaveSwitchDetails } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<SpiderMasterSlaveSwitchDetails>;
  }

  interface RowData {
    masterIp: string;
    slaveIp: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = infos.reduce((results, item) => {
    item.switch_tuples.forEach((tuple) => {
      results.push({
        masterIp: tuple.master.ip,
        slaveIp: tuple.slave.ip,
      });
    });
    return results;
  }, [] as RowData[]);

  const columns = [
    {
      label: t('主库主机'),
      field: 'masterIp',
      showOverflowTooltip: true,
    },
    {
      label: t('从库主机'),
      field: 'slaveIp',
      showOverflowTooltip: true,
    },
  ];
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
