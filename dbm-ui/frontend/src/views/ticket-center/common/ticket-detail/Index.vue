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
  <ScrollFaker v-if="isStretchLayoutSplited">
    <BkLoading
      class="ticket-details-page"
      :loading="isLoading"
      style="min-height: calc(100vh - 104px - var(--notice-height))">
      <PermissionCatch :key="ticketId">
        <SmartAction :offset-target="getOffsetTarget">
          <template v-if="ticketData">
            <BaseInfo :ticket-data="ticketData" />
            <DbCard
              :collapse="false"
              mode="collapse"
              :title="t('需求信息')">
              <TaskInfo :data="ticketData" />
              <div class="ticket-details-item">
                <span class="ticket-details-item-label">{{ t('备注') }}：</span>
                <span class="ticket-details-item-value">{{ ticketData.remark || '--' }}</span>
              </div>
            </DbCard>
            <DbCard
              class="ticket-flows"
              mode="collapse"
              :title="t('实施进度')">
              <FlowInfos :data="ticketData" />
              <!-- <FlowInfo
                :data="ticketData"
                @refresh="handleRefreshTicketData" /> -->
            </DbCard>
          </template>
          <template
            v-if="ticketData"
            #action>
            <TicketClone
              :data="ticketData"
              :text="false"
              theme="" />
          </template>
        </SmartAction>
      </PermissionCatch>
    </BkLoading>
  </ScrollFaker>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketDetails } from '@services/source/ticket';

  import { useEventBus, useStretchLayout } from '@hooks';

  import PermissionCatch from '@components/apply-permission/Catch.vue';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

  // import TicketClone from '@views/tickets/common/components/TicketClone.vue';
  import { useTimeoutFn } from '@vueuse/core';

  import BaseInfo from './components/BaseInfo.vue';
  import FlowInfos from './components/flow-info/Index.vue';
  import TaskInfo from './components/task-info/Index.vue';

  interface Props {
    ticketId: number;
  }

  const props = defineProps<Props>();

  const eventBus = useEventBus();
  const { t } = useI18n();
  const { isSplited: isStretchLayoutSplited } = useStretchLayout();

  const getOffsetTarget = () => document.body.querySelector('.ticket-details-page .db-card');

  const isLoading = ref(true);
  const ticketData = shallowRef<TicketModel<unknown>>();

  const { runAsync: fetchTicketDetails } = useRequest(
    (params: ServiceParameters<typeof getTicketDetails>) =>
      getTicketDetails(params, {
        permission: 'catch',
      }),
    {
      onSuccess(data, params) {
        if (params[0].id !== props.ticketId) {
          return;
        }
        ticketData.value = data;
        loopFetchTicketDetails();
      },
    },
  );

  const refreshTicketData = () => {
    fetchTicketDetails({
      id: props.ticketId,
    });
  };

  const { start: loopFetchTicketDetails } = useTimeoutFn(refreshTicketData, 1000000);

  watch(
    () => props.ticketId,
    () => {
      if (props.ticketId) {
        isLoading.value = true;
        ticketData.value = undefined;
        fetchTicketDetails({
          id: props.ticketId,
        }).finally(() => {
          isLoading.value = false;
        });
      }
    },
    {
      immediate: true,
    },
  );

  eventBus.on('refreshTicketStatus', refreshTicketData);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', refreshTicketData);
  });
</script>

<style lang="less">
  @import '@views/tickets/common/styles/ticketDetails.less';

  .ticket-details-page {
    padding: 24px;
    font-size: 12px;
    background: #f5f7fa;

    .bk-table {
      .bk-table-body {
        height: unset !important;
        max-height: unset !important;
      }

      td {
        height: unset !important;
        min-height: 42px;
      }
    }

    .db-card {
      .db-card__content {
        padding-left: 82px;
      }

      & ~ .db-card {
        margin-top: 16px;
      }
    }

    .ticket-flows {
      margin-bottom: 20px;

      .flow-todo__title {
        padding-bottom: 12px;
        font-weight: bold;
      }
    }

    .ticket-flow-content {
      .ticket-flow-content-desc {
        padding: 8px 0 24px;
        font-size: @font-size-mini;
        color: @title-color;
      }

      .ticket-flow-content-buttons {
        text-align: right;

        .bk-button {
          min-width: 62px;
          margin-left: 8px;
          font-size: @font-size-mini;
        }
      }
    }
  }
</style>
