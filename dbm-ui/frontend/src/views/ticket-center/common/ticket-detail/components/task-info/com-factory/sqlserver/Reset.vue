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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="cluster_id">
    <TableColumn
      col-key="cluster_id"
      :title="t('集群ID')" />
    <TableColumn
      col-key="new_cluster_name"
      :title="t('新集群')" />
    <TableColumn
      col-key="new_immutable_domain"
      :title="t('主域名')" />
    <TableColumn
      col-key="new_slave_domain"
      :title="t('从域名')" />
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.Reset>;
  }

  defineOptions({
    name: TicketTypes.SQLSERVER_RESET,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
