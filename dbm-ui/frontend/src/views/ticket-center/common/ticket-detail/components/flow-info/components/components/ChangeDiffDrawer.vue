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
  <BkSideslider
    v-model:is-show="isShow"
    render-directive="if"
    :width="960">
    <template #header>
      <span>{{ t('变更对比') }}</span>
      <span
        v-if="record"
        class="ticket-modify-diff-drawer-subtitle">
        {{ record.modeText }} ·
        <bk-user-display-name :user-id="record.operator" />
        · {{ record.createAtDisplay }}
      </span>
    </template>
    <div
      v-if="record"
      class="ticket-modify-diff-drawer">
      <ModifyRemarkBlock
        v-if="record.remark"
        :content="record.remark" />
      <DiffTable :data="record.change_details" />
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModifyRecordModel from '@services/model/ticket/modify-record';

  import DiffTable from '@views/ticket-center/common/ticket-modify/DiffTable.vue';
  import ModifyRemarkBlock from '@views/ticket-center/common/ticket-modify/ModifyRemarkBlock.vue';

  interface Props {
    record?: TicketModifyRecordModel;
  }

  withDefaults(defineProps<Props>(), {
    record: undefined,
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
</script>
<style lang="less">
  .ticket-modify-diff-drawer-subtitle {
    display: inline-flex;
    margin-left: 16px;
    font-size: 12px;
    font-weight: normal;
    color: #979ba5;
    align-items: center;
    gap: 4px;
  }

  .ticket-modify-diff-drawer {
    padding: 16px 24px;
    font-size: 12px;
  }
</style>
