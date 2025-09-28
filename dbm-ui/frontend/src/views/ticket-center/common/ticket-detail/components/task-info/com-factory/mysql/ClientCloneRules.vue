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
  <BkTable
    class="mysql-client-clone-render-table"
    :data="ticketDetails.details.clone_data"
    :show-overflow="false">
    <BkTableColumn :label="t('源客户端IP')">
      <template #default="{ data }: { data: RowData }">
        {{ `${data.bk_cloud_id}:${data.source}` }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('所属模块')">
      <template #default="{ data }: { data: RowData }">
        {{ data.module }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('新客户端IP')">
      <template #default="{ data }: { data: RowData }">
        <div class="render-target">
          <template
            v-for="(item, index) in data.target"
            :key="index">
            <p class="pt-2 pb-2">
              {{ item }}
            </p>
          </template>
          <DbIcon
            class="db-icon-copy"
            type="copy"
            :v-bk-tooltips="t('复制IP')"
            @click="copyIp(data.target)" />
        </div>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mysql.ClientCloneRules>;
  }

  type RowData = Props['ticketDetails']['details']['clone_data'][number];

  defineOptions({
    name: TicketTypes.MYSQL_CLIENT_CLONE_RULES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const copyIp = (data: string[]) => {
    execCopy(data.join('\n'), t('复制成功，共n条', { n: data.length }));
  };
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
