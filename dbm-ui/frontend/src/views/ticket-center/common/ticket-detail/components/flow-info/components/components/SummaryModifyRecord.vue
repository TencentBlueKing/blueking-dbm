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

<!-- 主摘要上的改单信息：紧跟主摘要行的「，变更对比（N 项）」与下一行的修改原因，用于只有一次处理的步骤 -->
<template>
  <span>，</span>
  <BkButton
    text
    theme="primary"
    @click="handleShowDiff">
    {{ t('变更对比（n 项）', { n: changeCount }) }}
  </BkButton>
  <div
    v-if="record.remark"
    class="summary-modify-record-remark">
    <span class="summary-modify-record-remark-label">{{ t('修改原因：') }}</span>
    <ClampText
      class="summary-modify-record-remark-text"
      :lines="2"
      :text="record.remark" />
  </div>
  <ChangeDiffDrawer
    v-model:is-show="isShowDiff"
    :modify-records="modifyRecords"
    :record="record"
    :ticket-data="ticketDetail" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import ClampText from '@views/ticket-center/common/ticket-modify/ClampText.vue';
  import { getTicketModifyDiffOptions } from '@views/ticket-center/common/ticket-modify/registry';
  import { diffDetails, getRecordDetailsPair } from '@views/ticket-center/common/ticket-modify/utils';

  import ChangeDiffDrawer from './ChangeDiffDrawer.vue';

  interface Props {
    modifyRecords: TicketModifyRecordModel[];
    record: TicketModifyRecordModel;
    ticketDetail: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowDiff = ref(false);

  // 相对上一版的差异项数，与记录块同一口径
  const changeCount = computed(() => {
    const { next, prev } = getRecordDetailsPair(props.modifyRecords, props.record.id, props.ticketDetail.details);
    return diffDetails(prev, next, getTicketModifyDiffOptions(props.ticketDetail.ticket_type)).length;
  });

  const handleShowDiff = () => {
    isShowDiff.value = true;
  };
</script>
<style lang="less">
  .summary-modify-record-remark {
    display: flex;
    margin-top: 8px;
    line-height: 20px;
    color: #63656e;

    .summary-modify-record-remark-label {
      flex-shrink: 0;
    }

    .summary-modify-record-remark-text {
      flex: 1;
      min-width: 0;
    }
  }
</style>
