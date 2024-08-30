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
  <BkLoading
    :loading="state.isLoading"
    style="min-height: calc(100vh - 120px)">
    <PermissionCatch :key="ticketId">
      <SmartAction :offset-target="getOffsetTarget">
        <div class="ticket-details-page">
          <template v-if="state.ticketData">
            <DbCard
              mode="collapse"
              :title="t('基本信息')">
              <Baseinfo
                :columns="baseColumns"
                :data="state.ticketData"
                width="30%" />
            </DbCard>
            <Teleport
              :disabled="!isFullscreen"
              to="body">
              <DbCard
                v-model:collapse="demandCollapse"
                :class="{ 'tickets-main-is-fullscreen': isFullscreen }"
                mode="collapse"
                :title="t('需求信息')">
                <DemandInfo
                  :data="state.ticketData"
                  :is-loading="state.isLoading" />
                <div class="mt-10">
                  <span>{{ t('备注') }}:</span>
                  <span class="ml-5">{{ state.ticketData.remark || '--' }}</span>
                </div>
              </DbCard>
            </Teleport>
            <DbCard
              class="ticket-flows"
              mode="collapse"
              :title="t('实施进度')">
              <FlowInfo
                ref="flowInfoRef"
                :data="state.ticketData"
                @refresh="handleRefreshTicketData" />
            </DbCard>
          </template>
        </div>
        <template
          v-if="state.ticketData"
          #action>
          <TicketClone :data="state.ticketData" />
        </template>
      </SmartAction>
    </PermissionCatch>
  </BkLoading>
</template>
<script lang="tsx">
  let myTicketsDetailTimer = 0;
</script>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import type { LocationQueryValue } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketDetails } from '@services/source/ticket';

  import PermissionCatch from '@components/apply-permission/Catch.vue';
  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import Baseinfo, { type InfoColumn } from '@views/tickets/common/components/baseinfo/Index.vue';
  import TicketClone from '@views/tickets/common/components/TicketClone.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import DemandInfo from './components/Demand.vue';
  import FlowInfo from './components/flow/Index.vue';

  interface Props {
    ticketId: number;
  }

  const props = defineProps<Props>();

  /**
   * 获取单据详情
   */
  const fetchTicketDetails = (id: number, isPoll = false) => {
    state.isLoading = !isPoll;
    getTicketDetails({ id }, {
      permission: 'catch'
    })
      .then((ticketData) => {
        state.ticketData = ticketData;

        if (currentScope?.active && ['PENDING', 'RUNNING'].includes(state.ticketData?.status)) {
          myTicketsDetailTimer = setTimeout(() => {
            fetchTicketDetails(id, true);
          }, 10000)
        }
      })
      .catch(() => {
        state.ticketData = null;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  const currentScope = getCurrentScope();
  const { t } = useI18n();
  const route = useRoute();

  const isFullscreen = ref<LocationQueryValue | LocationQueryValue[]>();
  const demandCollapse = ref(false);
  const flowInfoRef = ref<InstanceType<typeof FlowInfo>>()

  const state = reactive({
    isLoading: false,
    ticketData: null as TicketModel<unknown> | null,
  });

  /**
   * 基础信息配置
   */
  const baseColumns: InfoColumn[][] = [
    [
      {
        label: t('单号'),
        key: 'id',
      },
      {
        label: t('单据类型'),
        key: 'ticket_type_display',
      },
    ],
    [
      {
        label: t('单据状态'),
        key: 'status',
        render: () => {
          if (state.ticketData) {
            return <bk-tag theme={state.ticketData.tagTheme}>{t(state.ticketData.statusText)}</bk-tag>;
          }
          return <bk-tag theme={undefined} />;
        },
      },
      {
        label: t('申请人'),
        key: 'creator',
      },
    ],
    [
      {
        label: t('已耗时'),
        key: 'cost_time',
        render: () => (
          <CostTimer
            value={state.ticketData?.cost_time || 0}
            isTiming={state.ticketData?.status === 'RUNNING'}
            startTime={utcTimeToSeconds(state.ticketData?.create_at)} />
        ),
      },
      {
        label: t('申请时间'),
        key: 'create_at',
        render: () => (state.ticketData?.create_at ? utcDisplayTime(state.ticketData.create_at) : '--'),
      },
    ],
  ];

  watch(() => props.ticketId, () => {
    if (props.ticketId) {
      clearTimeout(myTicketsDetailTimer);
      fetchTicketDetails(props.ticketId);
    }
  }, { immediate: true });

  watch(isFullscreen, (isFullscreen) => {
    if (isFullscreen) {
      demandCollapse.value = true;
    }
  }, { immediate: true });

  watch(() => route.query.isFullscreen, (value) => {
    setTimeout(() => {
      isFullscreen.value = value;
    });
  }, {
    immediate: true,
  });

  const getOffsetTarget = () => document.body.querySelector('.ticket-details-page .db-card')

  const exitFullscreen = (e: KeyboardEvent) => {
    if (e.keyCode === 27) {
      isFullscreen.value = undefined;
    }
  };

  const handleRefreshTicketData = () => {
    fetchTicketDetails(props.ticketId);
  };

  onMounted(() => {
    window.addEventListener('keydown', exitFullscreen);
  });

  onBeforeUnmount(() => {
    clearTimeout(myTicketsDetailTimer);
    window.removeEventListener('keydown', exitFullscreen);
  });
</script>

<style lang="less">
  .ticket-details-page {
    padding: 24px;
    font-size: 12px;

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
