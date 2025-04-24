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
      class="ticket-details-box"
      :loading="isLoading">
      <PermissionCatch :key="ticketId">
        <SmartAction
          :offset-target="getOffsetTarget"
          :teleport-to="smartActionTeleportTo">
          <div
            v-if="ticketData"
            class="pb-20">
            <BaseInfo
              v-if="isDetailPage"
              :ticket-data="ticketData" />
            <TaskInfo
              :key="ticketId"
              :data="ticketData" />
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
          </template>
        </SmartAction>
      </PermissionCatch>
    </BkLoading>
  </ScrollFaker>
</template>
<script setup lang="tsx">
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketDetails } from '@services/source/ticket';

  import PermissionCatch from '@components/apply-permission/Catch.vue';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';
  import TicketRevoke from '@views/ticket-center/common/TicketRevoke.vue';

  import BaseInfo from './components/BaseInfo.vue';
  import FlowInfos from './components/flow-info/Index.vue';
  import TaskInfo from './components/task-info/Index.vue';

  interface Props {
    smartActionTeleportTo?: string;
    ticketId: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    smartActionTeleportTo: 'body',
  });

  const route = useRoute();

  const getOffsetTarget = () => document.body.querySelector('.ticket-details-box .db-card');

  const isDetailPage = route.name === 'ticketDetail';

  const isLoading = ref(true);
  const ticketData = shallowRef<TicketModel>();

  const { runAsync: fetchTicketDetails } = useRequest(
    (params: ServiceParameters<typeof getTicketDetails>) =>
      getTicketDetails(params, {
        cache: 1000,
        permission: 'catch',
      }),
    {
      onSuccess(data, params) {
        if (params[0].id !== props.ticketId) {
          return;
        }
        ticketData.value = data;
      },
    },
  );

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
</script>

<style lang="less">
  .ticket-details-box {
    min-height: 300px;
    font-size: 12px;

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
