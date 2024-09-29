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
  <div class="ticket-detail-flow-info">
    <BkLoading :loading="isLoading">
      <DbTimeLine>
        <template
          v-for="(item, index) in flowList"
          :key="index">
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
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketFlows } from '@services/source/ticketFlow';

  import FlowTypeBase from './components/FlowTypeBase.vue';
  import DbTimeLine from './components/time-line/Index.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

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
  const flowList = ref<ServiceReturnType<typeof getTicketFlows>>([]);

  const { runAsync: fetchTicketFlows } = useRequest(getTicketFlows, {
    manual: true,
    onSuccess(data, params) {
      if (params[0].id !== props.data.id) {
        return;
      }
      flowList.value = data;
    },
  });

  watch(
    () => props.data,
    (newData, oldData) => {
      if (props.data) {
        isLoading.value = newData.id !== oldData?.id;
        fetchTicketFlows({
          id: props.data.id,
        }).finally(() => {
          isLoading.value = false;
        });
      }
    },
    {
      immediate: true,
    },
  );

  // const handleFecthData = () => {
  //   fetchTicketFlows({
  //     id: props.data.id,
  //   });
  //   emits('refresh'); // 操作单据后立即查询基本信息
  // };
</script>

<style lang="less">
  .ticket-detail-flow-info {
    display: block;
  }
</style>
