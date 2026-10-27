<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkButton
    v-if="isRender"
    theme="primary"
    @click="handleReEdit">
    {{ t('重新编辑') }}
  </BkButton>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketStatus } from '@services/source/ticket';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { isTicketModifiable } from '@views/ticket-center/common/ticket-modify/registry';
  import useOpenTicketModify from '@views/ticket-center/common/ticket-modify/useOpenTicketModify';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { username } = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();
  const openTicketModify = useOpenTicketModify();

  const localStatus = ref('');

  // 只有提单人且单据类型已接入时才可能出现入口，其余情况不查状态、不轮询
  const isReEditable = computed(() => props.data.creator === username && isTicketModifiable(props.data.ticket_type));

  // 待审批下的重新编辑在底部与「撤销单据」同排；待确认修改下的入口在确认步骤里
  const isRender = computed(() => localStatus.value === TicketModel.STATUS_APPROVE && isReEditable.value);

  const { refresh: refreshTicketStatus } = useRequest(
    () =>
      getTicketStatus({
        ticket_ids: `${props.data.id}`,
      }),
    {
      manual: true,
      onSuccess(data) {
        localStatus.value = data[props.data.id];
        if (localStatus.value === TicketModel.STATUS_APPROVE) {
          loopFetchTicketStatus();
        }
      },
    },
  );

  // 不自动启动：轮询只在按条件发起的查询成功后续上，自动启动的定时器会绕过条件
  const { start: loopFetchTicketStatus } = useTimeoutFn(
    () => {
      refreshTicketStatus();
    },
    3000,
    {
      immediate: false,
    },
  );

  const handleRefreshTicketStatus = () => {
    if (isReEditable.value) {
      refreshTicketStatus();
    }
  };

  watch(
    () => props.data,
    () => {
      localStatus.value = props.data.status;
      handleRefreshTicketStatus();
    },
    {
      immediate: true,
    },
  );

  const handleReEdit = () => {
    openTicketModify(props.data, TicketModifyRecordModel.MODE_RE_EDIT);
  };

  eventBus.on('refreshTicketStatus', handleRefreshTicketStatus);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', handleRefreshTicketStatus);
  });
</script>
