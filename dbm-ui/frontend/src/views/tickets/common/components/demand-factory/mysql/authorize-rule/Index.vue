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
  <div class="mysql-table">
    <RenderTable
      v-bind="props"
      :data="data" />
  </div>
  <div
    v-if="showExcel"
    class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('Excel文件') }}：</span>
      <span class="ticket-details-item-value">
        <i class="db-icon-excel" />
        <a :href="ticketDetails.details.excel_url">{{ t('批量授权文件') }} <i class="db-icon-import" /></a>
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { MysqlAuthorizationDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  import { AccountTypes, TicketTypes } from '@common/const';

  import RenderTable from './components/RenderTable.vue';

  interface Props {
    ticketDetails: TicketModel<MysqlAuthorizationDetails>;
    accountType?: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountType: AccountTypes.MYSQL,
  });

  const { t } = useI18n();

  const showExcel = computed(() => props.ticketDetails.ticket_type === TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES);

  const data = computed(() => {
    // 导入授权
    if (props.ticketDetails.ticket_type === TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES) {
      return props.ticketDetails.details.authorize_data_list.map((item) => ({
        ips: item.source_ips as string[],
        user: item.user,
        accessDbs: item.access_dbs,
        clusterDomains: item.target_instances,
        privileges: item.privileges,
      }));
    }

    if (props.ticketDetails.ticket_type === TicketTypes.MYSQL_AUTHORIZE_RULES) {
      const { authorize_data: authorizeData } = props.ticketDetails.details;
      return [
        {
          ips: (authorizeData.source_ips as { ip: string }[]).map((item) => item.ip),
          user: authorizeData.user,
          accessDbs: authorizeData.access_dbs,
          clusterDomains: authorizeData.target_instances,
          privileges: authorizeData.privileges,
        },
      ];
    }
    return [];
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';

  .mysql-table {
    display: flex;

    span {
      display: inline;
      width: 160px;
      text-align: right;
    }
  }

  .db-icon-excel {
    margin-right: 5px;
    color: #2dcb56;
  }
</style>
