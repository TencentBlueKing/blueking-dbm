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
      {{ data.flow_info.flow_alias || data.flow_info.ticket_type_display || data.flow_info.root_id }}
    </span>
  </Teleport>
  <Teleport to="#dbContentHeaderAppend">
    <div class="mission-detail-status-box">
      <div
        v-if="statusInfo.text"
        class="mission-detail-status-info">
        <BkTag :theme="statusInfo.theme">
          {{ statusInfo.text }}
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
          class="top-operate-btn"
          :loading="isRevokeLoading">
          <DbIcon
            class="mr-4"
            type="stop" />
          {{ t('终止任务') }}
        </BkButton>
      </BkPopConfirm>
    </div>
    <div
      v-if="isSuperuserSwitchShow"
      class="mission-detail-super-user-box">
      <BkSwitcher
        v-model="isSuperUserMode"
        size="small"
        theme="primary" />
      <div
        v-bk-tooltips="t('专家模式：可对所有失败节点执行强制操作。强制操作将绕过系统预设的流程控制，请谨慎操作！')"
        class="box-text ml-4">
        {{ t('开启专家模式') }}
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { revokePipeline } from '@services/source/taskflow';

  import { useUserProfile } from '@stores';

  import { messageSuccess } from '@utils';

  import { type FlowDetail, type NodeStatusCount, superUserModeInjectionKey } from '../utils';

  interface Props {
    data?: FlowDetail;
    rootId?: string;
    /** 节点状态计数，由上层统一从解析结果算好，和搜索树的筛选下拉同一口径 */
    statusCount?: NodeStatusCount;
  }

  type Emits = (e: 'refresh') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    rootId: '',
    statusCount: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { isSuperuser } = useUserProfile();

  const isSuperUserMode = inject(superUserModeInjectionKey)!;

  // 任务级状态，与节点级不是一套：这里的 BLOCKED、等待执行是流程引擎自己的状态
  const TASK_STATUS_MAP = {
    BLOCKED: { text: t('执行中'), theme: 'info' },
    CREATED: { text: t('等待执行'), theme: undefined },
    FINISHED: { text: t('执行成功'), theme: 'success' },
    READY: { text: t('等待执行'), theme: undefined },
    REVOKED: { text: t('已终止'), theme: 'danger' },
    RUNNING: { text: t('执行中'), theme: 'info' },
  } as const;

  const taskStatus = computed(() => props.data?.flow_info.status);
  const isTaskFailed = computed(() => taskStatus.value === 'FAILED');
  // 数据还没回来，或者任务已经走完，都不允许再干预
  const isTaskOver = computed(() => !taskStatus.value || ['FINISHED', 'REVOKED'].includes(taskStatus.value));
  const isSuperuserSwitchShow = computed(() => isSuperuser && !isTaskOver.value);
  const todoNodesCount = computed(() => props.statusCount?.TODO ?? 0);
  const failNodesCount = computed(() => props.statusCount?.FAILED ?? 0);

  // 文案与配色一起给：此前拆成两个 computed，各写了一遍「失败优先于待继续」的判断
  const statusInfo = computed(() => {
    if (isTaskFailed.value) {
      return {
        text: t('执行失败'),
        theme: 'danger' as const,
      };
    }
    if (todoNodesCount.value) {
      return {
        text: t('待继续'),
        theme: 'warning' as const,
      };
    }
    return (
      TASK_STATUS_MAP[taskStatus.value as keyof typeof TASK_STATUS_MAP] ?? {
        text: '',
        theme: undefined,
      }
    );
  });

  const isRevokable = computed(() => !isTaskOver.value);

  const { loading: isRevokeLoading, run: runRevokePipeline } = useRequest(revokePipeline, {
    manual: true,
    onSuccess: () => {
      handleOperateSuccess();
    },
  });

  const handleOperateSuccess = () => {
    emits('refresh');
    messageSuccess(t('操作成功'));
  };

  const handleRevokePipeline = () => {
    runRevokePipeline({ rootId: props.rootId });
  };
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

  .mission-detail-super-user-box {
    display: flex;
    margin-left: auto;
    align-items: center;

    .box-text {
      font-size: 12px;
      color: #4d4f56;
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
