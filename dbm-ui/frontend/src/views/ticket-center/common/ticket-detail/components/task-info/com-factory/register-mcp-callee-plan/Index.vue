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

<template>
  <InfoList>
    <InfoItem :label="t('MCP 工具')">
      {{ details.mcp_id }}
    </InfoItem>
    <InfoItem :label="t('最大调用次数')">
      {{ details.max_call_count }}
    </InfoItem>
    <InfoItem :label="t('计划生效起始时间')">
      {{ details.time_window_start ? utcDisplayTime(details.time_window_start) : '--' }}
    </InfoItem>
    <InfoItem :label="t('计划生效截止时间')">
      {{ details.time_window_end ? utcDisplayTime(details.time_window_end) : '--' }}
    </InfoItem>
    <InfoItem :label="t('调用参数')">
      <pre class="demand-json-block">{{ formattedParams }}</pre>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Common } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Common.RegisterMcpCalleePlan>;
  }

  defineOptions({
    name: TicketTypes.REGISTER_MCP_CALLEE_PLAN,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const details = computed(() => props.ticketDetails.details);

  const formattedParams = computed(() => {
    const params = details.value.params;
    if (!params) return '';
    try {
      return JSON.stringify(params, null, 2);
    } catch {
      return String(params);
    }
  });
</script>

<style lang="less" scoped>
  .demand-json-block {
    background: #f5f7fa;
    border-radius: 2px;
    padding: 10px 14px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.8;
    color: #313238;
    white-space: pre;
    overflow: auto;
    max-height: 400px;
    margin: 0;
  }
</style>
