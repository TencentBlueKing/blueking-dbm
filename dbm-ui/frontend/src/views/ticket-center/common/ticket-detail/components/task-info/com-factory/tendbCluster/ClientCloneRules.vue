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
    :data="ticketDetails.details.clone_data"
    :show-overflow="false">
    <BkTableColumn :label="t('源客户端IP')">
      <template #default="{ data }: { data: RowData }">
        {{ data.source }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('所属模块')">
      <template #default="{ data }: { data: RowData }">
        {{ data.module }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('新客户端 IP')">
      <template #default="{ data }: { data: RowData }">
        <template
          v-for="(item, index) in data.target"
          :key="index">
          <p class="pt-2 pb-2">
            {{ item }}
            <i
              v-if="index === 0"
              class="db-icon-copy"
              :v-bk-tooltips="t('复制IP')"
              @click="copyIp(data.target)" />
          </p>
        </template>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCopy } from '@hooks';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ClientCloneRules>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const copy = useCopy();

  const copyIp = (data: string[]) => {
    copy(data.join('\n'));
  };

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
