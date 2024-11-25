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
  <InfoList>
    <InfoItem :label="t('变更类型:')">
      {{ t('删除规则') }}
    </InfoItem>
  </InfoList>
  <BkTable :data="[ticketDetails.details.last_account_rules]">
    <BkTableColumn
      field="userName"
      :label="t('账户名称')" />
    <BkTableColumn
      field="access_db"
      :label="t('访问DB')" />
    <BkTableColumn
      field="privilege"
      :label="t('权限')" />
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.AccountRuleChange>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
