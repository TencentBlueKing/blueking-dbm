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
  <Component
    :is="comMap[ticketDetails.details.action]"
    v-bind="props" />
</template>

<script setup lang="ts">
  import type { MySQLAccountRuleChangeDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  import { AccountTypes } from '@common/const';

  import PreviewDiff from './components/PreviewDiff.vue';
  import RuleDeleteTable from './components/RuleDeleteTable.vue';

  interface Props {
    ticketDetails: TicketModel<MySQLAccountRuleChangeDetails>;
    accountType?: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
  }

  const props = withDefaults(defineProps<Props>(), {
    accountType: AccountTypes.MYSQL,
  });

  const comMap = {
    change: PreviewDiff,
    delete: RuleDeleteTable,
  } as Record<string, any>;
</script>
