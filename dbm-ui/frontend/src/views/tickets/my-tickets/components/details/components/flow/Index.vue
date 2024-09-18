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
  <BkLoading :loading="isLoading">
    <Component
      :is="flowComponent"
      :key="data.id"
      :flows="flowList"
      :ticket-data="data"
      @fetch-data="handleFecthData" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketFlows } from '@services/source/ticket';

  import { TicketTypes } from '@common/const';

  import CommonFlows from './components/Common.vue';
  import MySqlDumpDataFlows from './components/MySqlDumpDataFlows.vue';
  import MySqlFlows from './components/MySqlFlows.vue';
  import RedisFlows from './components/RedisFlows.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isLoading = ref(true);
  const flowList = ref<ServiceReturnType<typeof getTicketFlows>>([]);

  const flowComponent = computed(() => {
    if ([TicketTypes.REDIS_KEYS_DELETE, TicketTypes.REDIS_KEYS_EXTRACT].includes(props.data.ticket_type)) {
      return RedisFlows;
    }
    if ([TicketTypes.MYSQL_IMPORT_SQLFILE, TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE].includes(props.data.ticket_type)) {
      return MySqlFlows;
    }
    if ([TicketTypes.MYSQL_DUMP_DATA, TicketTypes.TENDBCLUSTER_DUMP_DATA].includes(props.data.ticket_type)) {
      return MySqlDumpDataFlows;
    }
    return CommonFlows;
  });

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

  const handleFecthData = () => {
    fetchTicketFlows({
      id: props.data.id,
    });
    emits('refresh'); // 操作单据后立即查询基本信息
  };
</script>

<style lang="less" scoped>
  .ticket-flows {
    :deep(.db-card__content) {
      padding-left: 82px;
    }

    :deep(.bk-timeline) {
      padding-bottom: 16px;
    }

    :deep(.bk-timeline-title) {
      font-size: @font-size-mini;
      font-weight: bold;
      color: @title-color;
    }

    :deep(.bk-timeline-dot) {
      &::before {
        display: none;
      }

      .bk-timeline-icon {
        color: unset !important;
        background: white !important;
        border: none !important;
      }
    }

    :deep(.bk-timeline-content) {
      max-width: unset;
      font-size: @font-size-mini;
      color: @default-color;

      .flow-time {
        padding-top: 8px;
        color: @gray-color;
      }
    }

    :deep(.flow-todo) {
      &__title {
        padding-bottom: 12px;
        font-weight: bold;
      }
    }
  }
</style>

<style lang="less">
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
</style>
