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
  <div class="mysql-sql-execute-log-page">
    <Component :is="renderStatusCom" />
    <div class="sql-execute-more-action-box">
      <template v-if="flowStatus === 'failed'">
        <BkButton @click="handleGoEdit">
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
    <div
      v-if="flowStatus !== 'pending'"
      class="mt-16"
      style="padding: 0 45px">
      <BkTable :data="semanticExecuteResult">
        <BKTableColumn
          field="dbnames"
          :label="t('变更的 DB')"
          :width="200">
          <template #default="{ data }">
            <BkTag
              v-for="(tag, index) in data.dbnames"
              :key="index">
              {{ tag }}
            </BkTag>
          </template>
        </BKTableColumn>
        <BKTableColumn
          field="ignore_dbnames"
          :label="t('忽略的 DB')"
          :width="200">
          <template #default="{ data }">
            <template v-if="data.ignore_dbnames.length > 0">
              <BkTag
                v-for="(tag, index) in data.ignore_dbnames"
                :key="index">
                {{ tag }}
              </BkTag>
            </template>
            <span v-else>--</span>
          </template>
        </BKTableColumn>
        <BKTableColumn
          field="status"
          :label="t('SQL 文件执行结果')"
          :width="200">
          <template #default="{ data }">
            <span v-if="data.status === 'Failed'">
              <DbIcon
                svg
                type="sync-failed" />
              {{ t('失败') }}
            </span>
            <span v-else-if="data.status === 'Success'">
              <DbIcon
                svg
                type="sync-failed" />
              {{ t('失败') }}
            </span>
            <span v-else>
              <DbIcon
                svg
                type="sync-default" />
              {{ t('待执行') }}
            </span>
          </template>
        </BKTableColumn>
        <BKTableColumn :label="t('失败原因')">
          <template #default="{ data }">
            <div style="font-size: 12px; font-weight: bold; color: #ea3636; line-height: 22px">
              {{ data.file_name }}
            </div>
            <MultLineText
              :line="3"
              style="color: #63656e; line-height: 20px; margin-top: 4px">
              {{ data.err_msg }}
            </MultLineText>
          </template>
        </BKTableColumn>
      </BkTable>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import {
    deleteUserSemanticTasks,
    getSemanticExecuteResult,
    querySemanticData,
    revokeSemanticCheck,
  } from '@services/source/sqlImport';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import MultLineText from '@components/mult-line-text/Index.vue';

  import StatusFailed from './components/render-status/Failed.vue';
  import StatusPending from './components/render-status/Pending.vue';
  import StatusSuccess from './components/render-status/Success.vue';
  import useFlowStatus from './hooks/useFlowStatus';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const { rootId } = route.query as { rootId: string; nodeId: string };

  const ticketMode = ref('');
  const isSubmiting = ref(false);

  // 执行状态
  const { flowStatus, ticketId: flowTicketId } = useFlowStatus(rootId);

  // 执行状态
  const renderStatusCom = computed(() => {
    const statusComMap = {
      failed: StatusFailed,
      successed: StatusSuccess,
      pending: StatusPending,
    };

    return statusComMap[flowStatus.value as keyof typeof statusComMap];
  });

  const { data: semanticExecuteResult, run: runGetSemanticExecuteResult } = useRequest(getSemanticExecuteResult, {
    manual: true,
  });

  useRequest(querySemanticData, {
    defaultParams: [
      {
        root_id: rootId,
      },
    ],
    onSuccess(data) {
      ticketMode.value = data.ticket_mode.mode;
    },
  });

  const { loading: isRevokeing, run: runRevokeSemanticCheck } = useRequest(revokeSemanticCheck, {
    manual: true,
    onSuccess() {
      router.push({
        name: 'MySQLExecute',
      });
    },
  });

  const { loading: isDeleteing, run: runDeleteUserSemanticTasks } = useRequest(deleteUserSemanticTasks, {
    manual: true,
    onSuccess() {
      router.push({
        name: 'MySQLExecute',
      });
    },
  });

  // 执行成功自动跳转
  watch(
    flowStatus,
    () => {
      if (flowStatus.value !== 'pending') {
        runGetSemanticExecuteResult({
          root_id: rootId,
        });
      }
      if (flowStatus.value === 'successed') {
        router.push({
          name: 'MySQLExecute',
          params: {
            step: 'success',
          },
          query: {
            ticketId: flowTicketId.value,
            ticketMode: ticketMode.value,
          },
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 提交单据
  const handleSubmitTicket = () => {
    isSubmiting.value = true;
    createTicket({
      bk_biz_id: currentBizId,
      details: {
        root_id: rootId,
      },
      remark: '',
      ticket_type: 'MYSQL_IMPORT_SQLFILE',
    })
      .then((data) => {
        router.push({
          name: 'MySQLExecute',
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
      name: 'MySQLExecute',
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
    runRevokeSemanticCheck({
      root_id: rootId,
    });
  };

  const handleDeleteUserSemanticTasks = () => {
    runDeleteUserSemanticTasks({
      task_ids: [rootId],
      cluster_type: 'mysql',
    });
  };

  // 返回继续提单
  const handleLastStep = () => {
    router.push({
      name: 'MySQLExecute',
      params: {
        step: '',
      },
    });
  };
</script>
<style lang="less">
  .mysql-sql-execute-log-page {
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
