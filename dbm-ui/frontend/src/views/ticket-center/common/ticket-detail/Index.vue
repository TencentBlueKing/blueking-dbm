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
              :status="ticketStatus ?? ticketData.status"
              :ticket-data="ticketData" />
            <TaskInfo
              :key="ticketId"
              :data="ticketData"
              :modify-records="modifyRecords" />
            <FlowInfos
              :data="ticketData"
              :modify-records="modifyRecords" />
            <ContentUpdatedDialog
              :data="ticketData"
              @refresh="refreshTicketData" />
          </div>
          <template
            v-if="ticketData"
            #action>
            <TicketReEdit
              class="mr-8"
              :data="ticketData"
              :status="ticketStatus ?? ticketData.status" />
            <TicketClone
              class="mr-8"
              :data="ticketData"
              :text="false"
              theme="" />
            <TicketRevoke
              class="mr-8"
              :data="ticketData"
              :status="ticketStatus ?? ticketData.status" />
            <TicketTerminate
              class="mr-8"
              :data="ticketData"
              :status="ticketStatus ?? ticketData.status" />
          </template>
        </SmartAction>
      </PermissionCatch>
    </BkLoading>
  </ScrollFaker>
</template>
<script setup lang="tsx">
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketDetails, getTicketModifyRecords, getTicketStatus } from '@services/source/ticket';

  import { useEventBus } from '@hooks';

  import PermissionCatch from '@components/apply-permission/Catch.vue';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';
  import TicketReEdit from '@views/ticket-center/common/TicketReEdit.vue';
  import TicketRevoke from '@views/ticket-center/common/TicketRevoke.vue';
  import TicketTerminate from '@views/ticket-center/common/TicketTerminate.vue';

  import { useTimeoutFn } from '@vueuse/core';

  import BaseInfo from './components/BaseInfo.vue';
  import ContentUpdatedDialog from './components/ContentUpdatedDialog.vue';
  import FlowInfos from './components/flow-info/Index.vue';
  import TaskInfo from './components/task-info/Index.vue';

  interface Props {
    smartActionTeleportTo?: string;
    ticketId: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    smartActionTeleportTo: 'body',
  });

  const emits = defineEmits<Emits>();

  // 最新单据状态变化时抛给外层，外层（如列表侧滑详情的头部）不再自己轮询
  type Emits = (e: 'statusChange', value: TicketModel['status']) => void;

  const route = useRoute();
  const eventBus = useEventBus();

  const getOffsetTarget = () => document.body.querySelector('.ticket-details-box .db-card');

  const isDetailPage = route.name === 'ticketDetail';

  const isLoading = ref(true);
  const ticketData = shallowRef<TicketModel>();
  const modifyRecords = shallowRef<TicketModifyRecordModel[]>([]);
  // 轮询得到的最新单据状态，详情页内需要状态的组件统一从这里取，避免各自轮询
  const ticketStatus = ref<TicketModel['status']>();

  const { run: fetchTicketStatus } = useRequest(
    (ticketId: number) =>
      getTicketStatus({
        ticket_ids: `${ticketId}`,
      }),
    {
      manual: true,
      onSuccess(data, params) {
        // 切换单据后丢弃上一张单据的返回
        if (params[0] !== props.ticketId) {
          return;
        }
        ticketStatus.value = data[props.ticketId] as TicketModel['status'];
        emits('statusChange', ticketStatus.value);
        loopIfUnfinished(ticketStatus.value);
      },
    },
  );

  // 不自动启动：只在拿到未结束的状态后续上下一轮
  const { start: loopFetchTicketStatus } = useTimeoutFn(
    () => {
      fetchTicketStatus(props.ticketId);
    },
    3000,
    {
      immediate: false,
    },
  );

  // 单据未结束时继续轮询，判断与 TicketModel.isFinished 一致
  const loopIfUnfinished = (status: TicketModel['status']) => {
    if (![TicketModel.STATUS_SUCCEEDED, TicketModel.STATUS_TERMINATED].includes(status)) {
      loopFetchTicketStatus();
    }
  };

  const refreshTicketStatus = () => {
    fetchTicketStatus(props.ticketId);
  };

  const fetchModifyRecords = (ticketId: number) => {
    getTicketModifyRecords({ id: ticketId }).then((data) => {
      if (ticketId !== props.ticketId) {
        return;
      }
      // 接口返回顺序即版本递增，变更对比按索引取后一版，不重新排序
      modifyRecords.value = data;
    });
  };

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
        // 详情里已带最新状态，直接用它起步，3 秒后再开始查状态
        ticketStatus.value = data.status;
        loopIfUnfinished(data.status);
        fetchModifyRecords(data.id);
      },
    },
  );

  watch(
    () => props.ticketId,
    () => {
      if (props.ticketId) {
        isLoading.value = true;
        ticketData.value = undefined;
        ticketStatus.value = undefined;
        modifyRecords.value = [];
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

  const refreshTicketData = () => {
    fetchTicketDetails({
      id: props.ticketId,
    });
  };

  eventBus.on('refreshTicketData', refreshTicketData);
  eventBus.on('refreshTicketStatus', refreshTicketStatus);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketData', refreshTicketData);
    eventBus.off('refreshTicketStatus', refreshTicketStatus);
  });
</script>

<style lang="less">
  .ticket-details-box {
    min-height: 300px;
    font-size: 12px;

    .db-card {
      position: relative;
      z-index: 0;
      box-shadow: unset;

      .db-card-content {
        padding-left: 116px;
        overflow: hidden;
      }

      & ~ .db-card {
        margin-top: 16px;
      }
    }
  }
</style>
