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
  <template v-if="data.type === FlowMode.TODO_TYPE_CONFIRM_MODIFY">
    <Component
      :is="renderCom"
      :data="data"
      :flow-data="flowData"
      :modify-records="modifyRecords"
      :ticket-data="ticketData" />
  </template>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import StatusCommon from '../common';

  import useOpenConfirmModify from './hooks/useOpenConfirmModify';
  import StatusDoneSuccess from './StatusDoneSuccess.vue';
  import StatusTodo from './StatusTodo.vue';

  interface Props {
    data: FlowMode['todos'][number];
    flowData: FlowMode;
    modifyRecords: TicketModifyRecordModel[];
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { handleOpenConfirmModify } = useOpenConfirmModify();

  const renderCom = Object.assign({}, StatusCommon, {
    [FlowMode.TODO_STATUS_DONE_SUCCESS]: StatusDoneSuccess,
    [FlowMode.TODO_STATUS_TODO]: StatusTodo,
  })[props.data.status];

  onMounted(() => {
    // 单据已不在待确认修改时确认步骤不会挂载，直达链接在这里提示
    if (
      props.data.type === FlowMode.TODO_TYPE_CONFIRM_MODIFY &&
      props.ticketData.status !== TicketModel.STATUS_CONFIRM_PENDING
    ) {
      handleOpenConfirmModify(false);
    }
  });
</script>
