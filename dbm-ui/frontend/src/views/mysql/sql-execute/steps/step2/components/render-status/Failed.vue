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
  <div class="sql-execute-failed">
    <div class="wrapper">
      <span class="failed-flag">
        <DbIcon type="delete-fill" />
      </span>
    </div>
    <div style="margin-top: 22px; font-size: 24px; line-height: 32px; color: #313238">
      {{ t('模拟执行失败') }}
    </div>
    <div
      v-if="!isViewResultLog"
      style="margin-top: 8px; line-height: 32px; color: #313238">
      {{ t('接下你可以直接_继续提交_或_返回修改_后重试') }}
    </div>
  </div>
  <div class="sql-execute-more-action-box">
    <BkButton
      v-if="!isViewResultLog"
      @click="handleGoEdit">
      {{ t('返回修改') }}
    </BkButton>
    <BkButton
      v-if="!isViewResultLog"
      class="ml8 w-88"
      :loading="isSubmiting"
      theme="primary"
      @click="handleSubmitTicket">
      {{ t('继续提交') }}
    </BkButton>
    <DbPopconfirm
      v-if="!isViewResultLog"
      class="ml8"
      :confirm-handler="handleDeleteUserSemanticTasks"
      :content="t('返回修改会中断当前操作_请谨慎操作')"
      :title="t('确认终止')">
      <BkButton :loading="isDeleteing">
        {{ t('废弃') }}
      </BkButton>
    </DbPopconfirm>
    <BkButton
      v-if="isViewResultLog"
      class="ml8"
      @click="handleLastStep">
      {{ t('返回继续提单') }}
    </BkButton>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { deleteUserSemanticTasks } from '@services/source/sqlImport';
  import { createTicket } from '@services/source/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { rootId } = route.query as { rootId: string };
  const { step } = route.params as { step: string };

  // 查看执行结果日志，执行成功不自动提交
  const isViewResultLog = step === 'result';

  const isSubmiting = ref(false);

  const { loading: isDeleteing, run: runDeleteUserSemanticTasks } = useRequest(deleteUserSemanticTasks, {
    manual: true,
    onSuccess() {
      router.push({
        name: 'MySQLExecute',
      });
    },
  });

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

  // 提交单据
  const handleSubmitTicket = () => {
    isSubmiting.value = true;
    createTicket({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details: {
        root_id: rootId,
      },
      remark: '',
      ticket_type: TicketTypes.MYSQL_IMPORT_SQLFILE,
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

  const handleDeleteUserSemanticTasks = () => {
    runDeleteUserSemanticTasks({
      task_ids: [rootId],
      cluster_type: DBTypes.MYSQL,
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
<style lang="less" scoped>
  .sql-execute-failed {
    padding-top: 40px;
    text-align: center;

    .wrapper {
      display: flex;
      align-items: center;
      justify-content: center;

      .failed-flag {
        display: flex;
        width: 64px;
        height: 64px;
        font-size: 64px;
        color: #ea3636;
      }
    }

    .action-wrapper {
      display: flex;
      justify-content: center;
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
