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
  <DbCard
    v-model:collapse="isCardCollapse"
    mode="collapse"
    :title="t('实施进度')">
    <BkLoading :loading="isLoading">
      <DbTimeLine>
        <template
          v-for="item in flowList"
          :key="`${item.flow_type}#${item.status}`">
          <template v-if="flowTypeModule[item.flow_type]">
            <Component
              :is="flowTypeModule[item.flow_type]"
              :data="item"
              :ticket-detail="data" />
          </template>
          <FlowTypeBase
            v-else
            :data="item"
            :ticket-detail="data" />
        </template>
      </DbTimeLine>
    </BkLoading>
  </DbCard>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketFlows } from '@services/source/ticketFlow';

  import { useTimeoutFn } from '@vueuse/core';

  import FlowTypeBase from './components/FlowTypeBase.vue';
  import DbTimeLine from './components/time-line/Index.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: 'TicketFlowInfo',
  });

  const { t } = useI18n();

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

  const isCardCollapse = ref(true);
  const isLoading = ref(true);
  const flowList = shallowRef<ServiceReturnType<typeof getTicketFlows>>([]);

  const { refresh: refreshTicketFlows } = useRequest(
    () => {
      if (!props.data) {
        return Promise.reject();
      }
      return getTicketFlows({
        id: props.data.id,
      });
    },
    {
      manual: true,
      onSuccess(data) {
        flowList.value = data;
        loopFetchTicketStatus();
        isLoading.value = false;
      },
    },
  );

  watch(
    () => props.data,
    () => {
      isLoading.value = true;
      isCardCollapse.value = true;
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
