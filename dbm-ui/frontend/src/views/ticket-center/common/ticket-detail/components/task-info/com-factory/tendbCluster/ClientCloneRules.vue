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
  <TicketInfoTable
    class="mysql-client-clone-render-table"
    :data="ticketDetails.details.clone_data"
    ellipsis
    row-key="source">
    <TicketInfoTableColumn
      col-key="source"
      :get-copy-value="(row: RowData) => `${row.bk_cloud_id}:${row.source}`"
      :title="t('源客户端IP')">
      <template #default="{ row }: { row: RowData }">
        {{ `${row.bk_cloud_id}:${row.source}` }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="module"
      :title="t('所属模块')">
      <template #default="{ row }: { row: RowData }">
        {{ row.module }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target"
      :get-copy-value="(row: RowData) => row.target"
      :title="t('新客户端IP')">
      <template #default="{ row }: { row: RowData }">
        <div class="render-target">
          <template
            v-for="(item, index) in row.target"
            :key="index">
            <p class="pt-2 pb-2">
              {{ item }}
            </p>
          </template>
        </div>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ClientCloneRules>;
  }

  type RowData = Props['ticketDetails']['details']['clone_data'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .mysql-client-clone-render-table {
    .render-target {
      position: relative;
      width: 100px;

      .db-icon-copy {
        position: absolute;
        top: 8px;
        right: 14px;
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }

      &:hover {
        .db-icon-copy {
          display: block;
        }
      }
    }
  }
</style>
