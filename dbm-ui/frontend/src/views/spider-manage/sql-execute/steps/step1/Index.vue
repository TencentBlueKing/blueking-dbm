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
    <div class="spider-sql-execute-page">
      <TaskTips />
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData">
        <TargetCluster v-model="formData.cluster_ids" />
        <TargetDb
          v-model="formData.execute_db_infos"
          style="margin-top: 16px" />
        <SqlFile
          :key="resetFormKey"
          ref="sqlFileRef"
          v-model="formData.execute_sql_files"
          v-model:importMode="formData.import_mode"
          @grammar-check="handleGrammarCheck" />
        <BkFormItem
          :label="t('字符集')"
          property="charset"
          required>
          <BkSelect
            v-model="formData.charset"
            style="width: 360px">
            <BkOption value="default"> default </BkOption>
            <BkOption value="utf8mb4"> utf8mb4 </BkOption>
            <BkOption value="utf8"> utf8 </BkOption>
            <BkOption value="latin1"> latin1 </BkOption>
            <BkOption value="gbk"> gbk </BkOption>
            <BkOption value="gb2312"> gb2312 </BkOption>
          </BkSelect>
        </BkFormItem>
        <Backup v-model="formData.backup" />
        <ExecuteMode v-model="formData.ticket_mode" />
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
          {{ t('模拟执行') }}
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
  import { useRoute, useRouter } from 'vue-router';

  import { querySemanticData, semanticCheck } from '@services/source/sqlImport';

  import { useGlobalBizs } from '@stores';

  import Backup from './components/backup/Index.vue';
  import ExecuteMode from './components/ExecuteMode.vue';
  import SqlFile from './components/sql-file/Index.vue';
  import TargetDb from './components/target-db/Index.vue';
  import TargetCluster from './components/TargetCluster.vue';
  import TaskTips from './components/TaskTips.vue';

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();
  const { rootId } = route.query as { rootId: string | undefined };

  const createDefaultData = () => ({
    bk_biz_id: currentBizId,
    charset: 'default',
    cluster_ids: [],
    import_mode: 'manual',
    execute_sql_files: [],
    execute_db_infos: [],
    backup: [],
    ticket_mode: {
      mode: 'manual',
      trigger_time: '',
    },
    ticket_type: 'TENDBCLUSTER_SEMANTIC_CHECK',
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

  const fetchData = () => {
    if (!rootId) {
      return;
    }
    querySemanticData({
      bk_biz_id: currentBizId,
      root_id: rootId,
    }).then((data) => {
      const { semantic_data: semanticData } = data;
      Object.assign(formData, {
        charset: semanticData.charset,
        import_mode: semanticData.import_mode,
        cluster_ids: semanticData.cluster_ids,
        execute_sql_files: semanticData.execute_sql_files,
        execute_db_infos: semanticData.execute_db_infos,
        backup: semanticData.backup,
        ticket_mode: semanticData.ticket_mode,
      });
      updateFilePath.value = semanticData.path;
      submitButtonTips.disabled = true;
    });
  };

  fetchData();

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
      .then(() => {
        semanticCheck({
          ...formData,
          cluster_type: 'tendbcluster',
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'spiderSqlExecute',
            params: {
              step: 'log',
            },
            query: {
              rootId: data.root_id,
              nodeId: data.node_id,
            },
          });
        });
      })
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
  .spider-sql-execute-page {
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
