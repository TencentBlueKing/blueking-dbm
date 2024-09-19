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
  <PreviewDiff
    :account-type="AccountTypes.TENDBCLUSTER"
    :rules-form-data="rulesFormData" />
</template>

<script setup lang="ts">
  import type { MySQLAccountRuleChangeDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import type { AccountRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  import PreviewDiff from '../mysql/account-rule-change/components/PreviewDiff.vue';

  interface Props {
    ticketDetails: TicketModel<MySQLAccountRuleChangeDetails>;
  }

  const props = defineProps<Props>();

  const rulesFormData = reactive({
    beforeChange: {} as AccountRule,
    afterChange: {} as AccountRule,
  });

  watch(
    () => props.ticketDetails,
    () => {
      const {
        last_account_rules: lastAccountRules,
        account_id: accountId,
        access_db: accessDb,
        privilege,
      } = props.ticketDetails.details;
      rulesFormData.beforeChange = lastAccountRules;
      rulesFormData.afterChange = {
        account_id: accountId,
        access_db: accessDb,
        privilege,
      };
    },
    {
      immediate: true,
    },
  );
</script>
