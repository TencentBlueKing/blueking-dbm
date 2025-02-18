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
  <div class="tendb-cluster-sql-execute-log-page">
    <Component :is="renderStatusCom" />
    <div
      v-if="flowStatus !== 'pending'"
      class="mt-16"
      style="padding: 0 45px">
      <BkTable :data="semanticExecuteResult">
        <BkTableColumn
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
        </BkTableColumn>
        <BkTableColumn
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
        </BkTableColumn>
        <BkTableColumn
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
                type="sync-success" />
              {{ t('成功') }}
            </span>
            <span v-else>
              <DbIcon
                svg
                type="sync-default" />
              {{ t('待执行') }}
            </span>
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('失败原因')">
          <template #default="{ data }">
            <div v-if="data.status === 'Failed'">
              <div style="font-size: 12px; font-weight: bold; line-height: 22px; color: #ea3636">
                {{ getSQLFilename(data.file_name) }}
              </div>
              <MultlineText
                :line="3"
                style="margin-top: 4px; line-height: 20px; color: #63656e">
                {{ data.err_msg }}
              </MultlineText>
            </div>
            <div v-else>--</div>
          </template>
        </BkTableColumn>
      </BkTable>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getSemanticExecuteResult, querySemanticData } from '@services/source/mysqlSqlImport';

  import MultlineText from '@components/multline-text/Index.vue';

  import { getSQLFilename } from '@utils';

  import StatusFailed from './components/render-status/Failed.vue';
  import StatusPending from './components/render-status/Pending.vue';
  import StatusSuccess from './components/render-status/Success.vue';
  import useFlowStatus from './hooks/useFlowStatus';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { rootId } = route.query as { rootId: string; nodeId: string };
  const { step } = route.params as { step: string };

  const ticketMode = ref('');

  // 查看执行结果日志，执行成功不自动提交
  const isViewResult = step === 'result';

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

  // 执行成功自动跳转
  watch(
    flowStatus,
    () => {
      if (flowStatus.value !== 'pending') {
        runGetSemanticExecuteResult({
          root_id: rootId,
        });
      }
      if (flowStatus.value === 'successed' && !isViewResult) {
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
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .tendb-cluster-sql-execute-log-page {
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
  }
</style>
