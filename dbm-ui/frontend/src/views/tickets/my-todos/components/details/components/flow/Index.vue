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
  <BkLoading :loading="state.isLoading">
    <Component
      :is="flowComponent"
      :key="data.id"
      :flows="state.flows"
      @processed="handleProcessed" />
  </BkLoading>
</template>

<script setup lang="ts">
  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketFlows } from '@services/source/ticket';
  import type { FlowItem } from '@services/types/ticket';

  import { TicketTypes } from '@common/const';

  import { useTimeoutPoll } from '@vueuse/core';

  import ApproveFlows from './components/Approve.vue';
  import MySqlFlows from './components/MySqlFlows.vue';
  import RedisFlows from './components/RedisFlows.vue';

  interface Props {
    data: TicketModel;
  }

  interface Emits {
    (e: 'fetchData'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const currentScope = getCurrentScope();

  const state = reactive({
    isLoading: false,
    flows: [] as FlowItem[],
  });

  const flowComponent = computed(() => {
    if ([TicketTypes.REDIS_KEYS_DELETE, TicketTypes.REDIS_KEYS_EXTRACT].includes(props.data.ticket_type)) {
      return RedisFlows;
    }
    if ([TicketTypes.MYSQL_IMPORT_SQLFILE].includes(props.data.ticket_type)) {
      return MySqlFlows;
    }
    return ApproveFlows;
  });

  const needPollStatus = ['PENDING', 'RUNNING'];

  // 轮询
  const { isActive, resume, pause } = useTimeoutPoll(() => {
    fetchTicketFlows(props.data.id, true);
  }, 10000);

  watch(
    () => props.data.id,
    (id: number) => {
      if (id) {
        state.flows = [];
        fetchTicketFlows(id);
      }
    },
    { immediate: true },
  );

  /**
   * 获取单据流程
   */
  function fetchTicketFlows(id: number, isPoll = false) {
    state.isLoading = !isPoll;
    getTicketFlows({ id })
      .then((res) => {
        state.flows = res || [];
        // 设置轮询
        if (currentScope?.active) {
          !isActive.value && needPollStatus.includes(props.data?.status) && resume();
        } else {
          pause();
        }
      })
      .catch(() => {
        state.flows = [];
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleProcessed() {
    if (props.data.id) {
      fetchTicketFlows(props.data.id);
    }
    emits('fetchData'); // 操作单据后立即查询基本信息
  }
</script>

<style lang="less" scoped>
  .ticket-flows {
    :deep(.db-card__content) {
      padding-left: 82px;
    }

    :deep(.bk-timeline) {
      padding-bottom: 16px;

      .bk-timeline-title {
        font-size: @font-size-mini;
        font-weight: bold;
        color: @title-color;
      }

      .bk-timeline-dot {
        &::before {
          display: none;
        }

        .bk-timeline-icon {
          color: unset !important;
          background: unset !important;
          border: none !important;
        }
      }

      .bk-timeline-content {
        max-width: unset;
        font-size: @font-size-mini;
        color: @default-color;

        .flow-time {
          padding-top: 8px;
          color: @gray-color;
        }
      }

      .flow-todo {
        &__title {
          padding-bottom: 12px;
          font-weight: bold;
        }

        &__infos {
          margin-bottom: 8px;

          .done_success {
            color: @success-color;
          }

          .done_failed {
            color: @danger-color;
          }
        }
      }
    }
  }
</style>

<style lang="less">
  .todos-tips-content {
    &__desc {
      padding: 8px 0 24px;
      font-size: @font-size-mini;
      color: @title-color;
    }

    &__buttons {
      text-align: right;

      .bk-button {
        min-width: 62px;
        margin-left: 8px;
        font-size: @font-size-mini;
      }
    }
  }
</style>
