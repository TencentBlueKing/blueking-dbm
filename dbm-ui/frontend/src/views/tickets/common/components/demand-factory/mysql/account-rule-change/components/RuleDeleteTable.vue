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
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('变更类型') }}：</span>
      <span class="ticket-details-item-value">{{ t('删除规则') }}</span>
    </div>
  </div>
  <BkTable
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { MySQLAccountRuleChangeDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<MySQLAccountRuleChangeDetails>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('账户名称'),
      field: 'userName',
      width: 100,
    },
    {
      label: t('访问DB'),
      field: 'access_db',
      width: 100,
    },
    {
      label: t('权限'),
      field: 'privilege',
      width: 200,
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => <span>{cell.replace(/,/g, '，') || '--'}</span>
    },
  ];

  const tableData = computed(() => [props.ticketDetails.details.last_account_rules]);
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
