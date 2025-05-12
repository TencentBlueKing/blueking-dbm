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
    :loading="isLoading"
    style="min-height: 100px">
    <DbTimeLine>
      <template
        v-for="item in flowList"
        :key="`${item.flow_type}#${item.status}`">
        <template v-if="flowTypeModule[item.flow_type]">
          <Component
            :is="flowTypeModule[item.flow_type]"
            :data="item"
            :ticket-detail="ticketDetail" />
        </template>
        <FlowTypeBase
          v-else
          :data="item"
          :ticket-detail="ticketDetail" />
      </template>
    </DbTimeLine>
    <RelatedTicketFlow
      v-if="releateTicketFlow?.details.related_ticket"
      class="mt-16 ml-24"
      :ticket-id="releateTicketFlow.details.related_ticket" />
  </BkLoading>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useRequest } from 'vue-request';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketFlows } from '@services/source/ticketFlow';

  import { useTimeoutFn } from '@vueuse/core';

  import RelatedTicketFlow from './components/components/RelatedTicketFlow.vue';
  import FlowTypeBase from './components/FlowTypeBase.vue';
  import DbTimeLine from './components/time-line/Index.vue';

  interface Props {
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: 'TicketFlowInfo',
  });

  const props = defineProps<Props>();

  const flowTypeModule = Object.values(
    import.meta.glob<{
      default: {
        name: string;
      };
    }>('./components/flow-type-*/Index.vue', {
      eager: true,
    }),
  ).reduce<Record<string, Record<string, string>>>(
    (result, item) =>
      Object.assign(result, {
        [item.default.name]: item.default,
      }),
    {},
  );

  const isLoading = ref(true);
  const flowList = shallowRef<
    FlowMode<{
      related_ticket?: number;
    }>[]
  >([]);

  const releateTicketFlow = shallowRef<
    FlowMode<{
      related_ticket?: number;
    }>
  >();

  const { refresh: refreshTicketFlows } = useRequest(
    () => {
      if (!props.ticketDetail) {
        return Promise.reject();
      }
      return getTicketFlows<{
        related_ticket?: number;
      }>({
        id: props.ticketDetail.id,
      });
    },
    {
      manual: true,
      onSuccess(data) {
        flowList.value = _.filter(data, (item) => !item.details.related_ticket);
        releateTicketFlow.value = _.find(data, (item) => !!item.details.related_ticket);
        loopFetchTicketStatus();
        isLoading.value = false;
      },
    },
  );

  watch(
    () => props.ticketDetail,
    () => {
      isLoading.value = true;
      refreshTicketFlows();
    },
    {
      immediate: true,
    },
  );

  const { start: loopFetchTicketStatus } = useTimeoutFn(() => {
    refreshTicketFlows();
  }, 3000);
</script>
