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
  <IframeRender
    v-if="status === 'report'"
    auto-height
    :content="content"
    hide-head
    @anchor="handleAnchor"
    @panel-change="handlePanelChange" />
  <BkException
    v-else-if="status === 'empty'"
    class="health-report-content-exception"
    :description="t('报告每日约 06:00 生成上一自然日数据，生成后可在此查看。')"
    scene="part"
    :title="t('暂无健康报告')"
    type="empty" />
  <BkException
    v-else-if="status === 'noReport'"
    class="health-report-content-exception"
    :description="t('数据日期：{date}', { date: date || '--' })"
    scene="part"
    :title="t('该日无健康报告')"
    type="empty" />
  <BkException
    v-else-if="status === 'unsupported'"
    class="health-report-content-exception"
    scene="part"
    :title="t('暂不支持')"
    type="empty" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import IframeRender from '@views/ai-chat/share/components/IframeRender.vue';

  import type { HealthReportStatus } from '../hooks/useHealthReport';

  interface Props {
    content: string;
    date: string;
    status: HealthReportStatus | '';
  }

  // anchor：报告内锚点相对报告顶部的位置；panel-change：报告内要求切换的详情 Tab
  type Emits = {
    (e: 'anchor', top: number): void;
    (e: 'panel-change', panel: string): void;
  };

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleAnchor = (top: number) => emits('anchor', top);
  const handlePanelChange = (panel: string) => emits('panel-change', panel);
</script>
<style lang="less">
  .health-report-content-exception {
    &.bk-exception.bk-exception-part {
      height: 260px;
      padding-top: 48px;
      font-size: 12px;
    }
  }
</style>
