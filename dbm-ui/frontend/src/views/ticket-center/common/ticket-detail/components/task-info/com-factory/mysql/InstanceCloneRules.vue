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
  <InfoTable
    :data="ticketDetails.details.clone_data"
    row-key="cluster_id">
    <InfoTableColumn
      col-key="source"
      :get-copy-value="(item: Props['ticketDetails']['details']['clone_data'][number]) => item.source"
      :title="t('源实例')">
    </InfoTableColumn>
    <InfoTableColumn
      col-key="cluster_domain"
      :title="t('所属集群')">
    </InfoTableColumn>
    <InfoTableColumn
      col-key="target"
      :title="t('新实例')">
    </InfoTableColumn>
  </InfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoTable, { InfoTableColumn } from '../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.InstanceCloneRules>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
