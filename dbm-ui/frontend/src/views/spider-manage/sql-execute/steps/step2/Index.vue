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
  <div class="spider-sql-execute-log-page">
    <div>
      <Component :is="renderStatusCom" />
    </div>
    <div class="log-layout">
      <div
        v-if="isShowFileList"
        class="layout-left">
        <RenderFileList
          v-model="selectFileName"
          :file-log-map="fileLogMap"
          :flow-status="flowStatus"
          :list="fileDataList" />
      </div>
      <div
        class="layout-right"
        style="width: 928px;">
        <div class="log-header">
          <div>{{ t('执行日志') }}</div>
          <div
            v-if="currentSelectFileData?.isPending"
            class="log-status">
            <DbIcon
              class="rotate-loading"
              svg
              type="sync-pending" />
            <span style="padding-left: 4px; font-size: 12px;">{{ t('执行中') }}</span>
          </div>
          <div
            v-if="currentSelectFileData?.isFailed"
            class="log-status">
            <DbIcon
              style="color: #ea3636;"
              svg
              type="delete-fill" />
            <span style="padding-left: 4px; font-size: 12px;">{{ t('执行失败') }}</span>
          </div>
          <div
            v-if="currentSelectFileData?.isWaiting"
            class="log-status">
            <span style="padding-left: 4px; font-size: 12px;">{{ t('待执行') }}</span>
          </div>
        </div>
        <div style="height: calc(100vh - 476px);">
          <RenderLog :data="renderLog" />
        </div>
      </div>
    </div>
    <div class="sql-execute-more-action-box">
      <template v-if="flowStatus === 'failed'">
        <BkButton
          @click="handleGoEdit">
          {{ t('返回修改') }}
        </BkButton>
        <BkButton
          class="ml8 w-88"
          :loading="isSubmiting"
          theme="primary"
          @click="handleSubmitTicket">
          {{ t('继续提交') }}
        </BkButton>
        <DbPopconfirm
          class="ml8"
          :confirm-handler="handleDeleteUserSemanticTasks"
          :content="t('返回修改会中断当前操作_请谨慎操作')"
          :title="t('确认终止')">
          <BkButton :loading="isDeleteing">
            {{ t('废弃') }}
          </BkButton>
        </DbPopconfirm>
      </template>
      <template v-if="flowStatus === 'pending'">
        <DbPopconfirm
          class="ml8"
          :confirm-handler="handleRevokeSemanticCheck"
          :content="t('返回修改会中断当前操作_请谨慎操作')"
          :title="t('确认终止')">
          <BkButton :loading="isRevokeing">
            {{ t('终止执行') }}
          </BkButton>
        </DbPopconfirm>
        <BkButton
          class="ml8"
          @click="handleLastStep">
          {{ t('返回继续提单') }}
        </BkButton>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import {
    deleteUserSemanticTasks,
    querySemanticData,
    revokeSemanticCheck,
  } from '@services/sqlImport';
  import { createTicket } from '@services/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import RenderFileList, {
    type IFileItem,
  } from './components/render-file-list/Index.vue';
  import StatusFailed from './components/render-status/Failed.vue';
  import StatusPending from './components/render-status/Pending.vue';
  import StatusSuccess from './components/render-status/Success.vue';
  import RenderLog from './components/RenderLog.vue';
  import useFlowStatus from './hooks/useFlowStatus';
  import useLog from './hooks/useLog';

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const {
    rootId,
    nodeId,
  } = route.query as { rootId: string, nodeId: string };

  const selectFileName = ref('');
  const fileImportMode = ref('');
  const ticketMode = ref('');
  const fileNameList = ref<string []>([]);
  const isSubmiting = ref(false);
  const isRevokeing = ref(false);
  const isDeleteing = ref(false);
  const renderLog = shallowRef<any[]>([]);

  // 执行状态
  const {
    flowStatus,
    ticketId: flowTicketId,
  } = useFlowStatus(rootId);

  // 执行日志
  const {
    wholeLogList,
    fileLogMap,
  } = useLog(rootId, nodeId);

  // 执行状态
  const renderStatusCom = computed(() => {
    const statusComMap = {
      failed: StatusFailed,
      successed: StatusSuccess,
      pending: StatusPending,
    };

    return statusComMap[flowStatus.value as keyof typeof statusComMap];
  });

  const fileDataList = computed<IFileItem[]>(() => {
    const lastLogFileIndex = Math.max(Object.keys(fileLogMap.value).length - 1, 0);
    return fileNameList.value.map((name, index) => ({
      name,
      isPending: index === lastLogFileIndex && flowStatus.value === 'pending',
      isSuccessed: index < lastLogFileIndex || (index === lastLogFileIndex && flowStatus.value === 'successed'),
      isFailed: index === lastLogFileIndex && flowStatus.value === 'failed',
      isWaiting: index > lastLogFileIndex,
    }));
  });

  const currentSelectFileData = computed(() => _.find(
    fileDataList.value,
    item => item.name === selectFileName.value,
  ));
  // 本地文件需要显示文件列表
  const isShowFileList = computed(() => fileImportMode.value === 'file');

  watch([fileImportMode, selectFileName, fileLogMap], () => {
    if (fileImportMode.value === 'file') {
      // SQL 文件显示对应文件执行日志
      // 若没有任何一个文件的执行日志，则显示启动的完整的日志
      renderLog.value = fileLogMap.value[selectFileName.value] || wholeLogList.value;
    } else {
      // 手动输入显示所有文件
      renderLog.value = wholeLogList.value;
    }
  });

  // 执行成功自动跳转
  watch(flowStatus, () => {
    if (flowStatus.value === 'successed') {
      router.push({
        name: 'spiderSqlExecute',
        params: {
          step: 'success',
        },
        query: {
          ticketId: flowTicketId.value,
          ticketMode: ticketMode.value,
        },
      });
    }
  }, {
    immediate: true,
  });

  const fetchSemanticData = () => {
    querySemanticData({
      bk_biz_id: currentBizId,
      root_id: rootId,
    }).then((data) => {
      // 任务没成功轮询
      if (!data.sql_data_ready) {
        setTimeout(() => {
          fetchSemanticData();
        }, 2000);
        return;
      }
      fileImportMode.value = data.import_mode;
      fileNameList.value = data.semantic_data.execute_sql_files.map(item => item.replace(/[^_]+_/, ''));
      ticketMode.value = data.semantic_data.ticket_mode.mode;
      // 默认选中第一个问题件
      [selectFileName.value] = fileNameList.value;
    });
  };

  fetchSemanticData();

  // 提交单据
  const handleSubmitTicket = () => {
    isSubmiting.value = true;
    createTicket({
      bk_biz_id: currentBizId,
      details: {
        root_id: rootId,
      },
      remark: '',
      ticket_type: TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE,
    }).then((data) => {
      router.push({
        name: 'spiderSqlExecute',
        params: {
          step: 'success',
        },
        query: {
          ticketId: data.id,
        },
      });
    })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  // 执行失败返回编辑
  const handleGoEdit = () => {
    router.push({
      name: 'spiderSqlExecute',
      params: {
        step: '',
      },
      query: {
        rootId,
      },
    });
  };

  // 终止语义检测
  const handleRevokeSemanticCheck = () => {
    isRevokeing.value = true;
    return revokeSemanticCheck({
      bk_biz_id: currentBizId,
      root_id: rootId,
    }).then(() => {
      router.push({
        name: 'spiderSqlExecute',
      });
    })
      .finally(() => {
        isRevokeing.value = false;
      });
  };

  const handleDeleteUserSemanticTasks = () => {
    isDeleteing.value = true;
    return deleteUserSemanticTasks({
      bk_biz_id: currentBizId,
      task_ids: [rootId],
      cluster_type: 'tendbcluster',
    }).then(() => {
      router.push({
        name: 'spiderSqlExecute',
      });
    })
      .finally(() => {
        isDeleteing.value = false;
      });
  };

  // 返回继续提单
  const handleLastStep = () => {
    router.push({
      name: 'spiderSqlExecute',
      params: {
        step: '',
      },
    });
  };
</script>
<style lang="less">
  .spider-sql-execute-log-page {
    .log-layout {
      display: flex;
      width: 928px;
      margin: 0 auto;
      margin-top: 16px;
      overflow: hidden;
      border-radius: 2px;
      justify-content: center;

      .layout-left {
        width: 238px;
      }

      .layout-right {
        flex: 1;
      }

      .log-header {
        display: flex;
        height: 40px;
        padding: 0 20px;
        font-size: 14px;
        color: #fff;
        background: #2e2e2e;
        align-items: center;
      }

      .log-status {
        display: flex;
        padding-left: 14px;
        align-items: center;
        font-size: 12px;
      }
    }

    .bk-log {
      position: relative;
      z-index: 1;
    }

    .sql-execute-more-action-box {
      display: flex;
      margin-top: 12px;
      background: #fff;
      justify-content: center;
      align-items: center;
    }
  }
</style>
