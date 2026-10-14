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
      <div
        v-if="record.remark"
        class="ticket-modify-diff-drawer-remark">
        <span class="ticket-modify-diff-drawer-remark-label">{{ t('修改说明：') }}</span>
        <span>{{ record.remark }}</span>
      </div>
      <DiffTable :data="diffList" />
    </div>
    <template
      v-if="todoId"
      #footer>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleConfirm">
        {{ t('确认修改') }}
      </BkButton>
      <BkButton
        v-if="ticketData.creator === username"
        class="w-88 ml-8"
        :disabled="isSubmitting"
        @click="handleReEdit">
        {{ t('重新编辑') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import DiffTable from '@views/ticket-center/common/ticket-modify/DiffTable.vue';
  import { getTicketModifyDiffOptions } from '@views/ticket-center/common/ticket-modify/registry';
  import useOpenTicketModify from '@views/ticket-center/common/ticket-modify/useOpenTicketModify';
  import { diffDetails, getRecordDetailsPair } from '@views/ticket-center/common/ticket-modify/utils';

  import { messageSuccess } from '@utils';

  interface Props {
    modifyRecords: TicketModifyRecordModel[];
    record?: TicketModifyRecordModel;
    ticketData: TicketModel;
    // 传入确认修改待办 id 即为决策态，底部提供「确认修改 / 重新编辑」
    todoId?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    record: undefined,
    todoId: undefined,
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const eventBus = useEventBus();
  const { username } = useUserProfile();
  const openTicketModify = useOpenTicketModify();

  const isSubmitting = ref(false);

  const diffList = computed(() => {
    if (!props.record) {
      return [];
    }
    const { next, prev } = getRecordDetailsPair(props.modifyRecords, props.record.id, props.ticketData.details);
    return diffDetails(prev, next, getTicketModifyDiffOptions(props.ticketData.ticket_type));
  });

  const handleConfirm = () => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认修改'),
      content: t('确认后将沿用本次审批结论直接进入待执行，不再重新审批，且不可撤回。'),
      onConfirm: () => {
        isSubmitting.value = true;
        return batchProcessTodo({
          action: 'APPROVE',
          operations: [
            {
              params: {
                version: props.ticketData.version,
              },
              todo_id: props.todoId!,
            },
          ],
        })
          .then(() => {
            messageSuccess(t('操作成功'));
            isShow.value = false;
            eventBus.emit('refreshTicketStatus');
            eventBus.emit('refreshTicketData');
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      },
      title: t('确认修改？'),
    });
  };

  const handleReEdit = () => {
    openTicketModify(props.ticketData, TicketModifyRecordModel.MODE_RE_EDIT);
    isShow.value = false;
  };
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

    .ticket-modify-diff-drawer-remark {
      margin-bottom: 16px;
      line-height: 20px;
      color: #63656e;
      word-break: break-all;
      white-space: pre-wrap;

      .ticket-modify-diff-drawer-remark-label {
        color: #4d4f56;
      }
    }
  }
</style>
