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
  <div
    v-if="recordList.length > 0"
    class="ticket-modify-record-list">
    <div
      v-for="item in recordList"
      :key="item.id"
      class="ticket-modify-record-item">
      <div class="ticket-modify-record-row">
        <span>{{ item.createAtDisplay }}</span>
        <bk-user-display-name
          class="ml-8"
          :user-id="item.operator" />
        <span :class="{ 'ticket-modify-record-mode-on-behalf': item.mode === TicketModifyRecordModel.MODE_ON_BEHALF }">
          （{{ item.modeText }}）
        </span>
        <span>，</span>
        <BkButton
          text
          theme="primary"
          @click="() => handleShowDiff(item)">
          {{ t('变更对比（n 项）', { n: item.change_count }) }}
        </BkButton>
      </div>
      <div
        v-if="item.remark"
        class="ticket-modify-record-row ticket-modify-record-remark">
        <span class="ticket-modify-record-remark-label">{{ t('修改原因：') }}</span>
        <ClampText
          class="ticket-modify-record-remark-text"
          :lines="2"
          :text="item.remark" />
      </div>
    </div>
    <ChangeDiffDrawer
      v-model:is-show="isShowDiff"
      :record="currentRecord"
      :ticket-data="ticketDetail" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import ClampText from '@views/ticket-center/common/ticket-modify/ClampText.vue';

  import ChangeDiffDrawer from '../../components/ChangeDiffDrawer.vue';
  import { getSummaryRecord } from '../../components/summaryRecord';

  interface Props {
    flowData: FlowMode<unknown, any>;
    modifyRecords: TicketModifyRecordModel[];
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowDiff = ref(false);
  const currentRecord = shallowRef<TicketModifyRecordModel>();

  // 本步骤内的改单记录；接口顺序即版本递增，倒序后新的在上
  // 只有一次处理且已并入主摘要时，不再重复展示记录块
  const recordList = computed(() => {
    if (getSummaryRecord(props.flowData, props.modifyRecords)) {
      return [];
    }
    return props.modifyRecords.filter((item) => item.flow_id === props.flowData.id).reverse();
  });

  const handleShowDiff = (record: TicketModifyRecordModel) => {
    currentRecord.value = record;
    isShowDiff.value = true;
  };
</script>
<style lang="less">
  .ticket-modify-record-list {
    margin-top: 8px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .ticket-modify-record-item {
      padding: 8px 16px;
      background: #f5f7fa;
      border-radius: 2px;

      & ~ .ticket-modify-record-item {
        margin-top: 8px;
      }
    }

    .ticket-modify-record-row {
      position: relative;
      display: flex;
      padding-left: 12px;
      align-items: center;

      &::before {
        position: absolute;
        left: 0;
        content: '•';
      }
    }

    .ticket-modify-record-mode-on-behalf {
      color: #ff9c01;
    }

    .ticket-modify-record-remark {
      .ticket-modify-record-remark-label {
        flex-shrink: 0;
      }

      .ticket-modify-record-remark-text {
        flex: 1;
        min-width: 0;
      }
    }
  }
</style>
