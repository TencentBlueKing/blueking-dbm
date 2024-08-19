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
    class="details-ms-switch__table"
    :columns="columns"
    :data="ticketDetails.details.infos" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.RestoreSlave>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.SQLSERVER_RESTORE_SLAVE,
  });

  const { t } = useI18n();

  const columns = [
  {
      label: t('待重建从库主机'),
      field: 'new_slave_host.ip',
    },
    {
      label: t('同机关联集群'),
      field: 'immute_domain',
      render: ({ data }: { data: Props['ticketDetails']['details']['infos'][number] }) => data.cluster_ids.map((clusterId) => (
        <div style="line-height: 20px">{clusterId}</div>
      )),
    },
    {
      label: t('新从库主机'),
      field: 'old_slave_host.ip',
    },

  ];
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
