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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn :label="t('构造产物访问入口')">
      <template #default="{ row }">
        {{ row.display_info?.temp_cluster_proxy || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="prod_cluster"
      :label="t('源集群')" />
    <BkTableColumn
      field="related_rollback_bill_id"
      :label="t('关联单据')" />
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.DataStructureTaskDelete>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
