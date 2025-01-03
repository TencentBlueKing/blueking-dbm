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
  <StretchLayout
    v-if="!isPreChecking && !isTicketCountLoading"
    :key="isAssist ? 1 : 0"
    :left-width="400"
    :min-left-width="300"
    name="ticketList"
    style="background: #fff"
    @change="handleStretchLayoutChange">
    <template #list>
      <List />
    </template>
    <template #right>
      <Detail
        v-if="ticketId"
        :ticket-id="ticketId" />
    </template>
  </StretchLayout>
  <Teleport to="#dbContentTitleAppend">
    <div class="todo-ticket-action-box">
      <BkPopover placement="top">
        <DbIcon type="attention" />
        <template #content>
          <div>{{ t('待我处理：展示我作为主DBA 的业务，待我处理的单据') }}</div>
          <div>{{ t('待我协助：展示我作为协作人，备 DBA、二线 DBA 的业务，待我处理的单据') }}</div>
        </template>
      </BkPopover>
      <div class="split-line" />
      <div class="action-box">
        <div
          class="action-item"
          :class="{ 'is-active': !isAssist }"
          @click="handleChangeAssist(false)">
          <DbIcon
            class="mr-4"
            type="wodedaiban" />
          {{ t('待我处理') }} ({{ todoCount }})
        </div>
        <div class="split-line" />
        <div
          class="action-item"
          :class="{ 'is-active': isAssist }"
          @click="handleChangeAssist(true)">
          <DbIcon
            class="mr-4"
            type="yonghu-2" />
          {{ t('待我协助') }} ({{ todoHelperCount }})
        </div>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import { useTicketCount, useUrlSearch } from '@hooks';

  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import useDetailPreCheck from '@views/ticket-center/common/hooks/use-detail-precheck';
  import Detail from '@views/ticket-center/common/ticket-detail/Index.vue';

  import List from './components/list/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { getSearchParams } = useUrlSearch();

  const { t } = useI18n();

  const isAssist = ref(Boolean(Number(route.params.assist)));

  const ticketId = computed(() => Number(route.params.ticketId) || 0);

  const isPreChecking = useDetailPreCheck({
    id: ticketId.value,
    todo: 'running',
    self_manage: 1,
  });

  const { loading: isTicketCountLoading, data: ticketCount } = useTicketCount();

  const todoCount = computed(() => {
    if (!ticketCount.value) {
      return 0;
    }

    return (
      ticketCount.value.pending.APPROVE +
      ticketCount.value.pending.FAILED +
      ticketCount.value.pending.RESOURCE_REPLENISH +
      ticketCount.value.pending.INNER_TODO +
      ticketCount.value.pending.TODO
    );
  });

  const todoHelperCount = computed(() => {
    if (!ticketCount.value) {
      return 0;
    }

    return (
      ticketCount.value.to_help.APPROVE +
      ticketCount.value.to_help.FAILED +
      ticketCount.value.to_help.RESOURCE_REPLENISH +
      ticketCount.value.to_help.INNER_TODO +
      ticketCount.value.to_help.TODO
    );
  });

  const handleStretchLayoutChange = (value: boolean) => {
    if (!value) {
      router.replace({
        params: {
          ticketId: '',
        },
        query: {
          ...getSearchParams(),
          selectId: route.params.ticketId,
        },
      });
    }
  };

  const handleChangeAssist = (value: boolean) => {
    router.replace({
      params: {
        assist: value ? 1 : 0,
        status: '',
        ticketId: '',
      },
      query: {
        ...getSearchParams(),
      },
    });
    setTimeout(() => {
      isAssist.value = value;
    });
  };
</script>
<style lang="less">
  .todo-ticket-action-box {
    display: flex;
    align-items: center;
    margin-left: 8px;
    color: #979ba5;

    .split-line {
      width: 1px;
      height: 14px;
      margin: 0 14px;
      background: #c4c6cc;
    }

    .action-box {
      display: flex;
      height: 32px;
      background-color: #f0f1f5;
      align-items: center;
      border-radius: 2px;
    }

    .action-item {
      display: flex;
      padding: 0 8px;
      font-size: 14px;
      color: #4d4f56;
      align-items: center;
      cursor: pointer;

      &.is-active {
        font-weight: bold;
        color: #3a84ff;
        cursor: default;
        background-color: #f0f5ff;
      }
    }
  }
</style>
