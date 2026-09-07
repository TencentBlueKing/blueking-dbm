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
  <div
    ref="templateRef"
    class="task-history-flow-operation-main">
    <div class="title">
      {{ t('确认继续执行当前待继续节点？') }}
    </div>
    <div class="sub-title">{{ t('继续后将立即完成当前节点，并执行后续节点') }}</div>
    <div class="btn">
      <BkButton
        class="mr-8"
        :loading="continueLoading"
        size="small"
        theme="primary"
        @click.stop="handleContinueClick">
        {{ t('继续执行') }}
      </BkButton>
      <BkButton
        size="small"
        @click.stop="() => emits('close', false)">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { ticketBatchProcessTodo } from '@services/source/ticket';

  import { messageSuccess } from '@utils';

  import { type Node } from '../../utils';

  interface Props {
    data?: Node;
  }

  type Emits = (e: 'close', refresh: boolean) => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const { loading: continueLoading, run: runApproveTaskflowNode } = useRequest(ticketBatchProcessTodo, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('close', true);
    },
  });

  const templateRef = ref<HTMLDivElement>();

  const { t } = useI18n();

  const handleContinueClick = () => {
    if (props.data && props.data.todoId) {
      runApproveTaskflowNode({
        action: 'APPROVE',
        operations: [
          {
            params: {},
            todo_id: props.data.todoId,
          },
        ],
      });
    }
  };

  defineExpose({
    getTemplateRef() {
      return templateRef.value;
    },
  });
</script>
