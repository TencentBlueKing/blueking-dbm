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
  <ScrollFaker>
    <BkLoading
      class="ticket-details-page"
      :loading="isLoading"
      style="min-height: calc(100vh - 104px - var(--notice-height))">
      <PermissionCatch :key="ticketId">
        <SmartAction :offset-target="getOffsetTarget">
          <div
            v-if="ticketData"
            class="pb-20">
            <BaseInfo :ticket-data="ticketData" />
            <TaskInfo :data="ticketData" />
            <FlowInfos :data="ticketData" />
          </div>
          <template
            v-if="ticketData"
            #action>
            <TicketClone
              class="mr-8"
              :data="ticketData"
              :text="false"
              theme="" />
            <TicketRevoke
              class="mr-8"
              :data="ticketData" />
            <BkButton
              v-if="isShowGoDetail"
              @click="handleGoDetail">
              {{ t('新窗口打开') }}
            </BkButton>
          </template>
        </SmartAction>
      </PermissionCatch>
    </BkLoading>
  </ScrollFaker>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketDetails } from '@services/source/ticket';

  import { useEventBus } from '@hooks';

  import PermissionCatch from '@components/apply-permission/Catch.vue';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';
  import TicketRevoke from '@views/ticket-center/common/TicketRevoke.vue';

  import { useTimeoutFn } from '@vueuse/core';

  import BaseInfo from './components/BaseInfo.vue';
  import FlowInfos from './components/flow-info/Index.vue';
  import TaskInfo from './components/task-info/Index.vue';

  interface Props {
    ticketId: number;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const route = useRoute();
  const eventBus = useEventBus();
  const { t } = useI18n();

  const getOffsetTarget = () => document.body.querySelector('.ticket-details-page .db-card');

  const isShowGoDetail = route.name !== 'ticketDetail';

  const isLoading = ref(true);
  const ticketData = shallowRef<TicketModel>();

  const { runAsync: fetchTicketDetails } = useRequest(
    (params: ServiceParameters<typeof getTicketDetails>) =>
      getTicketDetails(params, {
        permission: 'catch',
        cache: 1000,
      }),
    {
      onSuccess(data, params) {
        if (params[0].id !== props.ticketId) {
          return;
        }
        ticketData.value = data;
        // 单据为完成继续下一次轮询
        if (!data.isFinished) {
          loopFetchTicketDetails();
        }
      },
    },
  );

  const refreshTicketData = () => {
    fetchTicketDetails({
      id: props.ticketId,
    });
  };

  const { start: loopFetchTicketDetails } = useTimeoutFn(refreshTicketData, 3000);

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

  const handleGoDetail = () => {
    const { href } = router.resolve({
      name: 'ticketDetail',
      params: {
        ticketId: props.ticketId,
      },
    });
    window.open(href);
  };

  eventBus.on('refreshTicketStatus', refreshTicketData);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', refreshTicketData);
  });
</script>

<style lang="less">
  .ticket-details-page {
    padding: 24px;
    font-size: 12px;
    background: #f5f7fa;

    .db-card {
      .db-card__content {
        padding-left: 116px;
        overflow: hidden;
      }

      & ~ .db-card {
        margin-top: 16px;
      }
    }
  }
</style>
