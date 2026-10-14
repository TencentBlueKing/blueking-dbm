<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<!-- 变更对比表：仅列有差异项，修改前置灰加删除线，列表字段默认折叠 3 行 -->
<template>
  <TicketInfoTable
    class="ticket-modify-diff-table"
    :data="data"
    row-key="path">
    <TicketInfoTableColumn
      col-key="label"
      :title="t('变更项')" />
    <TicketInfoTableColumn
      col-key="prev"
      :title="t('修改前')">
      <template #default="{ row }: { row: DiffItem }">
        <ClampText
          class="ticket-modify-diff-table-prev"
          :expandable="row.isList"
          :lines="row.isList ? 3 : 0"
          :text="row.prev" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="next"
      :title="t('修改后')">
      <template #default="{ row }: { row: DiffItem }">
        <ClampText
          :expandable="row.isList"
          :lines="row.isList ? 3 : 0"
          :text="row.next" />
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import ClampText from './ClampText.vue';
  import type { DiffItem } from './utils';

  interface Props {
    data: DiffItem[];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .ticket-modify-diff-table {
    .ticket-modify-diff-table-prev {
      color: #979ba5;
      text-decoration: line-through;
    }
  }
</style>
