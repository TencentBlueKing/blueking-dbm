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
  <Teleport to="#dbContentTitleAppend">
    <span v-if="data?.flow_info">
      <span class="ml-8 mr-6">|</span>
      {{ baseInfo.ticket_type_display }}
    </span>
  </Teleport>
  <Teleport to="#dbContentHeaderAppend">
    <div class="mission-detail-status-box">
      <div
        v-if="statusText"
        class="mission-detail-status-info">
        <BkTag :theme="statueTheme">
          {{ statusText }}
          <span
            v-if="isTaskFailed"
            class="top-count is-failed">
            {{ failNodesCount }}
          </span>
          <span
            v-else-if="todoNodesCount"
            class="top-count is-todo">
            {{ todoNodesCount }}
          </span>
        </BkTag>
      </div>
      <BkPopConfirm
        v-if="isRevokable"
        :content="t('确定终止任务吗')"
        trigger="click"
        width="288"
        @confirm="handleRevokePipeline">
        <BkButton
          ref="revokeButtonRef"
          class="top-operate-btn"
          :loading="isRevokeLoading">
          <DbIcon
            class="mr-4"
            type="stop" />
          {{ t('终止任务') }}
        </BkButton>
      </BkPopConfirm>
    </div>
  </Teleport>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { revokePipeline } from '@services/source/taskflow';

  import { messageSuccess } from '@utils';

  import { type FlowDetail } from '../Index.vue';

  import TaskFlow from './task-flow/Index.vue';

  interface Props {
    data?: FlowDetail;
    rootId?: string;
  }

  type Emits = (e: 'refresh') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    rootId: '',
  });
  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const taskFlowRef = ref<InstanceType<typeof TaskFlow>>();

  const baseInfo = computed(() => props.data?.flow_info || ({} as FlowDetail['flow_info']));
  const isTaskFailed = computed(() => props.data?.flow_info.status === 'FAILED');

  const statusText = computed(() => {
    if (isTaskFailed.value) {
      return t('执行失败');
    }
    if (todoNodesCount.value) {
      return t('待继续');
    }
    const statusMap = {
      BLOCKED: t('执行中'),
      CREATED: t('等待执行'),
      // FAILED: t('执行失败'),
      FINISHED: t('执行成功'),
      READY: t('等待执行'),
      REVOKED: t('已终止'),
      RUNNING: t('执行中'),
    };
    const status = props.data?.flow_info.status as keyof typeof statusMap;
    return status && statusMap[status] ? t(statusMap[status]) : '';
  });

  const statueTheme = computed(() => {
    const status = props.data?.flow_info.status;
    if (isTaskFailed.value) {
      return 'danger';
    }
    if (todoNodesCount.value) {
      return 'warning';
    }
    const themes = {
      CREATED: 'default',
      FINISHED: 'success',
      RUNNING: 'info',
    };
    return themes[status as keyof typeof themes] || 'default';
  });

  const todoNodesCount = computed(() => {
    if (props.data?.flow_info) {
      const { status } = props.data.flow_info;
      return (props.data.todos || []).filter(
        (todoItem) => (status === 'RUNNING' || status === 'FAILED') && todoItem.status === 'TODO',
      ).length;
    }
    return 0;
  });

  const failNodesCount = computed(() => {
    let failNodesNum = 0;
    const getFailNodesNum = (activities: FlowDetail['activities']) => {
      const flowList: FlowDetail['activities'][string][] = [];
      Object.values(activities).forEach((item) => {
        if (item.status === 'FAILED') {
          if (item.pipeline) {
            getFailNodesNum(item.pipeline.activities);
          } else {
            failNodesNum = failNodesNum + 1;
          }
        }
      });
      return flowList;
    };
    getFailNodesNum(props.data?.activities || {});
    return failNodesNum;
  });

  const isRevokable = computed(() => {
    if (!props.data) {
      return false;
    }

    return !['FINISHED', 'REVOKED'].includes(baseInfo.value.status);
  });

  const { loading: isRevokeLoading, run: runRevokePipeline } = useRequest(revokePipeline, {
    manual: true,
    onSuccess: () => {
      handleOperateSuccess();
    },
  });

  watch(
    () => [isTaskFailed.value, todoNodesCount.value],
    () => {
      setTimeout(() => {
        if (isTaskFailed.value) {
          taskFlowRef.value?.setTreeStatus('FAILED');
          return;
        }

        if (todoNodesCount.value) {
          taskFlowRef.value?.setTreeStatus('TODO');
          return;
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleOperateSuccess = () => {
    emits('refresh');
    messageSuccess(t('操作成功'));
  };

  const handleRevokePipeline = () => {
    runRevokePipeline({ rootId: props.rootId });
  };

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
  .mission-detail-status-box {
    display: flex;
    margin-left: 12px;
    font-size: 12px;

    .mission-detail-status-info {
      display: flex;
      align-items: center;
      margin-right: 8px;

      .bk-tag-text {
        display: inline-flex;
        align-items: center;

        .top-count {
          display: inline-block;
          height: 16px;
          padding: 0 3px;
          margin-left: 6px;
          font-size: 12px;
          line-height: 12px;
          text-align: center;
          border-radius: 8px;

          &.is-failed {
            color: #ffebeb;
            background: #ea3636;
            border: 2px solid #ffebeb;
          }

          &.is-todo {
            color: #fdeed8;
            background: #f59500;
            border: 2px solid #fdeed8;
          }
        }
      }
    }

    .top-operate-btn {
      height: 26px;
      font-size: 12px;

      i {
        font-size: 14px;
      }
    }
  }
</style>
