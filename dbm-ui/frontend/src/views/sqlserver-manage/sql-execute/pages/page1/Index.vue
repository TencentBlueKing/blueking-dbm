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
  <SmartAction>
    <div class="sqlserver-sql-execute-page">
      <TaskTips />
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData">
        <ClusterIds v-model="formData.cluster_ids" />
        <ExecuteDbInfos
          v-model="formData.execute_db_infos"
          style="margin-top: 16px" />
        <ExecuteSqlFiles
          :key="resetFormKey"
          ref="sqlFileRef"
          v-model="formData.execute_sql_files"
          @grammar-check="handleGrammarCheck" />
        <BkFormItem
          :label="t('字符集')"
          property="charset"
          required>
          <BkSelect
            v-model="formData.charset"
            style="width: 360px">
            <BkOption value="GBK"> GBK </BkOption>
          </BkSelect>
        </BkFormItem>
        <Backup
          v-model="formData.backup"
          :cluster-id-list="formData.cluster_ids" />
        <TicketMode v-model="formData.ticket_mode" />
      </DbForm>
    </div>
    <template #action>
      <span
        v-bk-tooltips="{
          ...submitButtonTips,
        }">
        <BkButton
          class="w-88"
          :disabled="!submitButtonTips.disabled"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
      </span>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts">
  import { reactive, ref } from 'vue';

  export const updateFilePath = ref('');
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/source/ticket';

  import Backup from './components/backup/Index.vue';
  import ClusterIds from './components/ClusterIds.vue';
  import ExecuteDbInfos from './components/execute-db-infos/Index.vue';
  import ExecuteSqlFiles from './components/execute-sql-file/Index.vue';
  import TaskTips from './components/TaskTips.vue';
  import TicketMode from './components/TicketMode.vue';

  const router = useRouter();

  const createDefaultData = () => ({
    charset: 'GBK',
    cluster_ids: [],
    import_mode: 'manual',
    execute_sql_files: [],
    execute_db_infos: [],
    backup: [],
    ticket_mode: {
      mode: 'manual',
      trigger_time: '',
    },
    ticket_type: 'SQLSERVER_IMPORT_SQLFILE',
  });

  const { t } = useI18n();

  const formRef = ref();
  const sqlFileRef = ref();
  const formData = reactive(createDefaultData());
  const submitButtonTips = reactive({
    disabled: false,
    content: t('先执行语法检测'),
  });

  const resetFormKey = ref(0);

  const isSubmitting = ref(false);

  const handleGrammarCheck = (doCheck: boolean, passed: boolean) => {
    if (!doCheck) {
      submitButtonTips.disabled = false;
      submitButtonTips.content = t('先执行语法检测');
      return;
    }
    if (!passed) {
      submitButtonTips.disabled = false;
      submitButtonTips.content = t('语法检测不通过，请先修正');
      return;
    }
    submitButtonTips.disabled = true;
    submitButtonTips.content = '';
  };

  // 开始模拟执行
  const handleSubmit = () => {
    isSubmitting.value = true;

    formRef.value
      .validate()
      .then(() =>
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          ticket_type: 'SQLSERVER_IMPORT_SQLFILE',
          details: {
            ...formData,
          },
        }).then(() => {
          window.changeConfirm = false;
          router.push({
            name: 'sqlServerExecute',
            params: {
              page: 'success',
            },
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    resetFormKey.value = resetFormKey.value + 1;
    Object.assign(formData, createDefaultData());
  };
</script>

<style lang="less">
  .sqlserver-sql-execute-page {
    padding-bottom: 40px;

    .bk-form-label {
      font-weight: bold;
      color: #313238;

      &::after {
        line-height: unset !important;
      }
    }
  }
</style>
