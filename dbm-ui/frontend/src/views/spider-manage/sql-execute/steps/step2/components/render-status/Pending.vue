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
  <div class="sql-execute-pending">
    <div class="wrapper">
      <span class="loading-flag rotate-loading">
        <DbIcon
          svg
          type="sync-pending" />
      </span>
    </div>
    <div style="margin-top: 22px; font-size: 24px; line-height: 32px; color: #313238">
      {{ t('模拟执行正在进行中_请稍等') }}
    </div>
    <div style="margin-top: 8px; line-height: 32px; color: #313238">
      <p>{{ t('模拟执行成功后自动提交单据，模拟失败将暂停提交。') }}</p>
      <p>{{ t('强制失败将立刻停止模拟执行，如确认SQL无误可继续提交单据。') }}</p>
    </div>
  </div>
  <div class="sql-execute-more-action-box">
    <DbPopconfirm
      v-if="!isViewResultLog"
      class="ml8"
      :confirm-handler="handleRevokeSemanticCheck"
      :content="t('返回修改会中断当前操作_请谨慎操作')"
      :title="t('确认强制失败？')">
      <BkButton :loading="isRevokeing">
        {{ t('强制失败') }}
      </BkButton>
    </DbPopconfirm>
    <BkButton
      class="ml8"
      @click="handleLastStep">
      {{ t('返回继续提单') }}
    </BkButton>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { revokeSemanticCheck } from '@services/source/sqlImport';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { rootId } = route.query as { rootId: string };
  const { step } = route.params as { step: string };

  // 查看执行结果日志
  const isViewResultLog = step === 'result';

  const { loading: isRevokeing, run: runRevokeSemanticCheck } = useRequest(revokeSemanticCheck, {
    manual: true,
  });

  const handleRevokeSemanticCheck = () => {
    runRevokeSemanticCheck({
      root_id: rootId,
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
<style lang="less" scoped>
  .sql-execute-pending {
    padding-top: 40px;
    text-align: center;

    .wrapper {
      display: flex;
      align-items: center;
      justify-content: center;

      .loading-flag {
        display: flex;
        width: 64px;
        height: 64px;
        font-size: 64px;
        color: #3a84ff;
      }
    }
  }
  .sql-execute-more-action-box {
    display: flex;
    margin-top: 12px;
    background: #fff;
    justify-content: center;
    align-items: center;
  }
</style>
