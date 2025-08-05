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
  <RouteHeader
    :data="currentTaskflowDetail"
    :root-id="rootId"
    @refresh="fetchTaskflowDetails" />
  <BkLoading :loading="!currentTaskflowDetail">
    <div
      ref="missionDetailPageRef"
      class="mission-detail-page">
      <div class="basic-info-main">
        <div class="item">
          <div class="title">ID：</div>
          <div class="content">{{ currentTaskflowDetail?.id }}</div>
        </div>
        <div class="item">
          <div class="title">{{ t('业务') }}：</div>
          <div class="content">{{ baseInfo.bk_biz_name }}</div>
        </div>
        <div class="item">
          <div class="title">{{ t('执行人') }}：</div>
          <div class="content">{{ baseInfo.created_by }}</div>
        </div>
        <div class="item">
          <div class="title">{{ t('关联单据') }}：</div>
          <div class="content">
            <BkButton
              text
              theme="primary"
              @click="handleShowRelatedTicketDetail">
              {{ baseInfo.uid }}
            </BkButton>
          </div>
        </div>
        <div class="item">
          <div class="title">{{ t('创建时间') }}：</div>
          <div class="content">{{ utcDisplayTime(baseInfo.created_at) }}</div>
        </div>
        <div class="item">
          <div class="title">{{ t('结束时间') }}：</div>
          <div class="content">{{ utcDisplayTime(baseInfo.updated_at) }}</div>
        </div>
        <div class="item">
          <div class="title">{{ t('已耗时') }}：</div>
          <div class="content">
            <CostTimer
              :is-timing="baseInfo.status === 'RUNNING'"
              :start-time="utcTimeToSeconds(baseInfo.created_at)"
              :value="baseInfo.cost_time || 0" />
          </div>
        </div>
        <div
          v-if="baseInfo.bk_host_ids?.length"
          class="item">
          <div class="title">{{ t('涉及主机') }}：</div>
          <div class="content">
            <BkButton
              text
              theme="primary"
              @click="handleShowHostPreview">
              {{ baseInfo.bk_host_ids?.length || 0 }}
            </BkButton>
          </div>
        </div>
      </div>
      <BkTab
        v-model:active="activePanelId"
        class="detail-tab-main"
        type="card-grid">
        <BkTabPanel
          v-if="showDeliverResult"
          :label="t('交付结果')"
          name="deliver_result">
          <DeliverResult
            :root-id="rootId"
            :ticket-id="ticketId"
            @request-finish="handleDeliverList" />
        </BkTabPanel>
        <BkTabPanel
          :label="t('任务流程')"
          name="task_flow">
          <TaskFlow
            ref="taskFlowRef"
            :data="currentTaskflowDetail"
            @refresh="handleRefresh" />
        </BkTabPanel>
        <BkTabPanel
          :label="t('操作历史')"
          name="operate_history">
          <OperationHistory
            ref="operationHistoryRef"
            :root-id="rootId" />
        </BkTabPanel>
      </BkTab>
    </div>
  </BkLoading>
  <HostPreview
    v-model:is-show="showHostPreview"
    :biz-id="baseInfo.bk_biz_id"
    :host-ids="baseInfo.bk_host_ids || []" />
  <RelatedTicketDetail
    v-model:is-show="showRelatedTicketDetail"
    :ticket-id="Number(currentTaskflowDetail?.flow_info.uid)" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getTaskflowDetails } from '@services/source/taskflow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import DeliverResult, { type AbstractItem } from './components/DeliverResult.vue';
  import HostPreview from './components/HostPreview.vue';
  import OperationHistory from './components/OperationHistory.vue';
  import RelatedTicketDetail from './components/RelatedTicketDetail.vue';
  import RouteHeader from './components/RouteHeader.vue';
  import TaskFlow from './components/task-flow/Index.vue';

  export type FlowDetail = ServiceReturnType<typeof getTaskflowDetails>;

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  let isInitCanvas = false;

  const ticketId = ref(0);
  const showHostPreview = ref(false);
  const showDeliverResult = ref(true);
  const activePanelId = ref('deliver_result');
  const showRelatedTicketDetail = ref(false);
  const missionDetailPageRef = ref<HTMLElement>();
  const currentTaskflowDetail = ref<FlowDetail>();
  const taskFlowRef = ref<InstanceType<typeof TaskFlow>>();
  const operationHistoryRef = ref<InstanceType<typeof OperationHistory>>();

  const baseInfo = computed(() => currentTaskflowDetail.value?.flow_info || ({} as FlowDetail['flow_info']));
  const rootId = computed(() => route.params.root_id as string);

  const todoNodesCount = computed(() => {
    if (currentTaskflowDetail.value?.flow_info) {
      const { status } = currentTaskflowDetail.value.flow_info;
      return (currentTaskflowDetail.value.todos || []).filter(
        (todoItem) => (status === 'RUNNING' || status === 'FAILED') && todoItem.status === 'TODO',
      ).length;
    }
    return 0;
  });

  watch(activePanelId, () => {
    if (activePanelId.value === 'task_flow') {
      if (isInitCanvas) {
        return;
      }

      setTimeout(() => {
        isInitCanvas = true;
        taskFlowRef.value!.checkAndInitCanvas();
      }, 100);
    }
  });

  watch(
    () => baseInfo.value.status,
    () => {
      setTimeout(() => {
        if (baseInfo.value.status === 'FAILED') {
          taskFlowRef.value!.setTreeStatus('FAILED');
          return;
        }

        if (baseInfo.value.status === 'RUNNING') {
          taskFlowRef.value!.setTreeStatus('RUNNING');
          return;
        }
      });
    },
    {
      immediate: true,
    },
  );

  watch(
    todoNodesCount,
    () => {
      setTimeout(() => {
        if (todoNodesCount.value) {
          taskFlowRef.value!.setTreeStatus('TODO');
          return;
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleRefresh = () => {
    fetchTaskflowDetails();
    operationHistoryRef.value!.updateTableData();
  };

  const handleShowHostPreview = () => {
    showHostPreview.value = true;
  };

  const handleDeliverList = (list: AbstractItem[]) => {
    showDeliverResult.value = list.length > 0;
    if (!list.length) {
      activePanelId.value = 'task_flow';
    }
  };

  const handleShowRelatedTicketDetail = () => {
    showRelatedTicketDetail.value = true;
  };

  const fetchTaskflowDetails = () => {
    getTaskflowDetails(
      { rootId: rootId.value },
      {
        permission: 'page',
      },
    ).then((data) => {
      currentTaskflowDetail.value = data;
      ticketId.value = Number(data.flow_info.uid);
      if (showDeliverResult.value) {
        showDeliverResult.value = !!ticketId.value;
      }

      if (['FINISHED', 'REVOKED'].includes(data.flow_info.status)) {
        pause();
      }
    });
  };

  const { pause } = useTimeoutPoll(fetchTaskflowDetails, 30000);

  onMounted(() => {
    fetchTaskflowDetails();
  });

  onBeforeUnmount(() => {
    pause();
  });

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.push({
          name: 'taskHistoryList',
        });
        return;
      }
      router.push({
        name: route.query.from as string,
      });
    },
  });
</script>
<style lang="less">
  @import '@styles/mixins';

  .mission-detail-page {
    position: relative;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 104px);

    .basic-info-main {
      position: absolute;
      top: -5px;
      z-index: 99;
      display: flex;
      width: 100%;
      min-height: 30px;
      padding: 0 52px 10px;
      font-size: 12px;
      color: #979ba5;
      background: #fff;
      box-shadow: 0 3px 4px 0 #0000000a;
      align-items: center;

      .item {
        display: flex;
        margin-right: 20px;

        .content {
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      .operations {
        margin-left: auto;
      }
    }

    .detail-tab-main {
      flex: 1;
      margin: 45px 24px 16px;

      .bk-tab-content {
        max-height: calc(100vh - 200px);
        padding: 16px 0;
      }
    }
  }

  .task-history-flow-operation-main {
    width: 280px;
    padding: 12px 0 8px;
    color: @default-color;

    .title {
      font-size: 16px;
      color: #313238;
    }

    .sub-title {
      margin-top: 6px;
      margin-bottom: 16px;
      font-size: 12px;
      color: #63656e;
    }

    .btn {
      width: 100%;
      margin-top: 14px;
      text-align: right;

      .confirm {
        width: 88px;
        color: #fff;
        background: #ea3636;
        border: none;
      }

      .bk-button {
        height: 26px;
        padding: 0 12px;
        font-size: 12px;
      }
    }
  }
</style>
