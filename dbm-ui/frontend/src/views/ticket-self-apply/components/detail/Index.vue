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
            <Teleport
              :disabled="!isFullscreen"
              to="body">
              <DbCard
                v-model:collapse="demandCollapse"
                :class="{ 'tickets-main-is-fullscreen': isFullscreen }"
                mode="collapse"
                :title="t('需求信息')">
                <DemandInfo :data="ticketData" />
                <div class="ticket-details-item">
                  <span class="ticket-details-item-label">{{ t('备注') }}：</span>
                  <span class="ticket-details-item-value">{{ ticketData.remark || '--' }}</span>
                </div>
              </DbCard>
            </Teleport>
            <DbCard
              class="ticket-flows"
              mode="collapse"
              :title="t('实施进度')">
              <FlowInfo
                ref="flowInfoRef"
                :data="ticketData"
                @refresh="handleRefreshTicketData" />
            </DbCard>
          </template>
          <template
            v-if="ticketData"
            #action>
            <TicketClone :data="ticketData" />
          </template>
        </SmartAction>
      </PermissionCatch>
    </BkLoading>
  </ScrollFaker>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTicketDetails } from '@services/source/ticket';

  import { useStretchLayout } from '@hooks';

  import PermissionCatch from '@components/apply-permission/Catch.vue';

  import TicketClone from '@views/tickets/common/components/TicketClone.vue';
  import BaseInfo from '@views/tickets/my-tickets/components/details/components/BaseInfo.vue';
  import DemandInfo from '@views/tickets/my-tickets/components/details/components/Demand.vue';
  import FlowInfo from '@views/tickets/my-tickets/components/details/components/flow/Index.vue';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    ticketId: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const { isSplited: isStretchLayoutSplited } = useStretchLayout();

  const getOffsetTarget = () => document.body.querySelector('.ticket-details-page .db-card');

  const isFullscreen = ref<boolean>(Boolean(route.query.isFullscreen));
  const demandCollapse = ref(false);
  const isLoading = ref(true);
  const flowInfoRef = ref<InstanceType<typeof FlowInfo>>();

  const { runAsync: fetchTicketDetails, data: ticketData } = useRequest(
    (params: ServiceParameters<typeof getTicketDetails>) =>
      getTicketDetails(params, {
        permission: 'catch',
      }),
    {
      onSuccess(_, params) {
        if (params[0].id !== props.ticketId) {
          return;
        }
        loopFetchTicketDetails();
      },
    },
  );

  const { start: loopFetchTicketDetails } = useTimeoutFn(() => {
    fetchTicketDetails({
      id: props.ticketId,
    });
  }, 10000);

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

  watch(
    isFullscreen,
    () => {
      if (isFullscreen.value) {
        demandCollapse.value = true;
      }
    },
    {
      immediate: true,
    },
  );

  const exitFullscreen = (e: KeyboardEvent) => {
    if (e.keyCode === 27) {
      isFullscreen.value = false;
    }
  };

  const handleRefreshTicketData = () => {
    fetchTicketDetails({
      id: props.ticketId,
    });
  };

  onMounted(() => {
    window.addEventListener('keydown', exitFullscreen);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', exitFullscreen);
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

    .bk-timeline {
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
          background: white !important;
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
