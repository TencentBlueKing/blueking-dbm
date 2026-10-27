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
  <div>
    <I18nT
      keypath="处理人_p"
      scope="global">
      <bk-user-display-name :user-id="data.operators.join(',')" />
    </I18nT>
    <I18nT
      v-if="ticketData.todo_helpers.length > 0"
      keypath="_协助人_p"
      scope="global">
      <bk-user-display-name :user-id="ticketData.todo_helpers.join(',')" />
    </I18nT>
    <I18nT
      keypath="_耗时_t"
      scope="global">
      <CostTimer
        is-timing
        :start-time="utcTimeToSeconds(flowData.start_time)"
        :value="flowData.cost_time" />
    </I18nT>
    <div
      v-if="isCanOperation"
      class="mt-12">
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleShowConfirm">
        {{ t('确认') }}
      </BkButton>
      <BkButton
        v-if="isCreator"
        class="w-88 ml-8"
        @click="handleReEdit">
        {{ t('重新编辑') }}
      </BkButton>
    </div>
    <ChangeDiffDrawer
      v-model:is-show="isShowConfirm"
      :record="pendingRecord"
      :ticket-data="ticketData"
      :todo-id="data.id" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import useOpenTicketModify from '@views/ticket-center/common/ticket-modify/useOpenTicketModify';

  import { utcTimeToSeconds } from '@utils';

  import ChangeDiffDrawer from '../../components/ChangeDiffDrawer.vue';

  import useOpenConfirmModify from './hooks/useOpenConfirmModify';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
    modifyRecords: TicketModifyRecordModel[];
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { username } = useUserProfile();
  const openTicketModify = useOpenTicketModify();
  const { handleOpenConfirmModify } = useOpenConfirmModify();

  const isShowConfirm = ref(false);

  // 确认步骤的处理人即提单人，协助人同样可以确认
  const isCanOperation = computed(
    () => props.data.operators.includes(username) || props.ticketData.todo_helpers.includes(username),
  );

  // 重新编辑只有提单人能发起，与改单页的进入校验一致
  const isCreator = computed(() => props.ticketData.creator === username);

  // 待确认的是最近一次代为修改
  const pendingRecord = computed(() =>
    _.findLast(props.modifyRecords, (item) => item.mode === TicketModifyRecordModel.MODE_ON_BEHALF),
  );

  const handleShowConfirm = () => {
    isShowConfirm.value = true;
  };

  const handleReEdit = () => {
    openTicketModify(props.ticketData, TicketModifyRecordModel.MODE_RE_EDIT);
  };

  onMounted(() => {
    handleOpenConfirmModify(isCanOperation.value, handleShowConfirm);
  });
</script>
