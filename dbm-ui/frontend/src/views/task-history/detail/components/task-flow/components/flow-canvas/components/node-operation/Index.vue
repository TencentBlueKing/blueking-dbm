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
    <div class="title">{{ operationConfig.title }}</div>
    <div class="sub-title">{{ operationConfig.subTitle }}</div>
    <div class="btn">
      <BkButton
        class="mr-8"
        :loading="isLoading"
        size="small"
        :theme="operationConfig.theme"
        @click.stop="handleConfirm">
        {{ operationConfig.confirmText }}
      </BkButton>
      <BkButton
        size="small"
        @click.stop="() => emits('close', false)">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script lang="ts">
  /** 画布节点卡片上可直接确认的操作，与节点上的操作图标一一对应 */
  export type NodeOperationType = 'continue' | 'forceFail' | 'retry' | 'skip';
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { forceFailflowNode, retryTaskflowNode, skipTaskflowNode } from '@services/source/taskflow';
  import { ticketBatchProcessTodo } from '@services/source/ticket';

  import { messageSuccess } from '@utils';

  import { type Node } from '../../utils';

  export interface Props {
    data?: Node;
    rootId: string;
    type: NodeOperationType;
  }

  type Emits = (e: 'close', refresh: boolean) => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  /** 每种操作只有文案、按钮主题和请求不同，气泡本身是同一个 */
  const operationConfigMap: Record<
    NodeOperationType,
    {
      confirmText: string;
      request: (node: Node, rootId: string) => Promise<unknown>;
      subTitle: string;
      theme: 'danger' | 'primary';
      title: string;
    }
  > = {
    continue: {
      confirmText: t('继续执行'),
      // 待继续节点才画得出「确认继续」图标，走到这里 todoId 一定有值
      request: (node) =>
        ticketBatchProcessTodo({
          action: 'APPROVE',
          operations: [
            {
              params: {},
              todo_id: node.todoId,
            },
          ],
        }),
      subTitle: t('继续后将立即完成当前节点，并执行后续节点'),
      theme: 'primary',
      title: t('确认继续执行当前待继续节点？'),
    },
    forceFail: {
      confirmText: t('强制失败'),
      request: (node, rootId) =>
        forceFailflowNode({
          node_id: node.id,
          root_id: rootId,
        }),
      subTitle: t('强制失败将立即终止节点运行，并标记为 “失败”'),
      theme: 'danger',
      title: t('确认强制终止当前执行中节点并置为失败？'),
    },
    retry: {
      confirmText: t('确认重试'),
      request: (node, rootId) =>
        retryTaskflowNode({
          node_id: node.id,
          root_id: rootId,
        }),
      subTitle: t('重试将重新执行当前节点'),
      theme: 'primary',
      title: t('确认重试当前失败节点？'),
    },
    skip: {
      confirmText: t('跳过节点'),
      request: (node, rootId) =>
        skipTaskflowNode({
          node_id: node.id,
          root_id: rootId,
        }),
      subTitle: t('跳过将忽略当前节点失败状态，直接执行后续节点，当前节点标记为“执行成功(失败手动跳过)”'),
      theme: 'primary',
      title: t('确认跳过当前失败节点？'),
    },
  };

  const templateRef = ref<HTMLDivElement>();

  const operationConfig = computed(() => operationConfigMap[props.type]);

  const { loading: isLoading, run: runOperation } = useRequest(
    (node: Node) => operationConfig.value.request(node, props.rootId),
    {
      manual: true,
      onSuccess: () => {
        messageSuccess(t('操作成功'));
        emits('close', true);
      },
    },
  );

  const handleConfirm = () => {
    if (!props.data) {
      return;
    }
    runOperation(props.data);
  };

  defineExpose({
    getTemplateRef() {
      return templateRef.value;
    },
  });
</script>
<style lang="less">
  .task-history-flow-operation-main {
    width: 280px;
    padding: 16px;
    color: @default-color;

    .title {
      font-size: 14px;
      color: #313238;
    }

    .sub-title {
      margin-top: 8px;
      font-size: 12px;
    }

    .btn {
      margin-top: 16px;
      text-align: right;
    }
  }
</style>
