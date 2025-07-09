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
    <InfoItem :label="t('目标集群')">
      {{ domainList.join('，') }}
    </InfoItem>
    <InfoItem :label="t('Excel 文件')">
      <div class="excel-link">
        <DbIcon
          class="mr-6"
          color="#2dcb56"
          svg
          type="excel" />
        <a :href="excelUrl">
          {{ t('批量授权文件') }}
          <DbIcon
            class="ml-6"
            svg
            type="import" />
        </a>
      </div>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.authorizeRules>;
  }

  defineOptions({
    name: TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES,
    inheritAttrs: false,
  });
  const props = defineProps<Props>();
  const { t } = useI18n();

  const domainList = props.ticketDetails.details.authorize_data?.[0].target_instances || [];
  const excelUrl = props.ticketDetails.details?.excel_url;
</script>

<style lang="less" scoped>
  :deep(.excel-link) {
    display: flex;
    align-items: center;
  }
</style>
