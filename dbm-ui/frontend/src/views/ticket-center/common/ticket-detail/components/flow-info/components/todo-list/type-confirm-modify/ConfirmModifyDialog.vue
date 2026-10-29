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

<!-- 提单人确认代为修改：弹窗内展示修改说明与变更对比，点确认直接提交，不再二次确认 -->
<template>
  <BkDialog
    :is-show="isShow"
    :quick-close="false"
    :title="t('确认修改内容')"
    :width="800"
    @closed="handleCancel">
    <!-- 先看修改说明再看变更明细 -->
    <div
      v-if="record?.remark"
      class="ticket-confirm-modify-dialog-remark">
      <span class="ticket-confirm-modify-dialog-remark-label">{{ t('修改说明：') }}</span>
      <span>{{ record.remark }}</span>
    </div>
    <div class="ticket-confirm-modify-dialog-tip">
      {{ t('确认后将沿用本次审批结论直接进入待执行，不再重新审批，且不可撤回。') }}
    </div>
    <DiffTable :data="record?.change_details || []" />
    <template #footer>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleConfirm">
        {{ t('确认') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import DiffTable from '@views/ticket-center/common/ticket-modify/DiffTable.vue';

  import { messageSuccess } from '@utils';

  interface Props {
    // 待确认的代为修改记录
    record?: TicketModifyRecordModel;
    ticketData: TicketModel;
    // 确认修改待办 id
    todoId: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    record: undefined,
  });

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isSubmitting = ref(false);

  // 确认即提交，按钮 loading 到接口返回；成功关闭弹窗并刷新单据，失败保持打开（请求层已提示错误）
  const handleConfirm = () => {
    if (isSubmitting.value) {
      return;
    }
    isSubmitting.value = true;
    batchProcessTodo({
      action: 'APPROVE',
      operations: [
        {
          params: {
            version: props.ticketData.version,
          },
          todo_id: props.todoId,
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
  };

  // 提交中不允许关闭
  const handleCancel = () => {
    if (isSubmitting.value) {
      return;
    }
    isShow.value = false;
  };
</script>
<style lang="less">
  .ticket-confirm-modify-dialog-remark {
    margin-bottom: 16px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    word-break: break-all;
    white-space: pre-wrap;

    .ticket-confirm-modify-dialog-remark-label {
      color: #4d4f56;
    }
  }

  .ticket-confirm-modify-dialog-tip {
    margin-bottom: 16px;
    font-size: 12px;
    color: #63656e;
  }
</style>
