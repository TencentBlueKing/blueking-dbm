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
    <div class="mongo-script-execute-page">
      <!-- <TaskTips /> -->
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData">
        <TargetCluster v-model="formData.cluster_ids" />
        <SqlFile
          :key="resetFormKey"
          ref="sqlFileRef"
          v-model="formData.execute_sqls"
          v-model:importMode="formData.import_mode" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="!isAbleSubmit"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
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
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import SqlFile from './components/sql-file/Index.vue';
  import TargetCluster from './components/TargetCluster.vue';
  // import TaskTips from './components/TaskTips.vue';

  const { currentBizId } = useGlobalBizs();
  const router = useRouter();

  const createDefaultData = () => ({
    cluster_ids: [],
    import_mode: 'manual',
    execute_sqls: [] as string[],
    execute_db_infos: [],
    backup: [],
  });

  const { t } = useI18n();

  const formRef = ref();
  const sqlFileRef = ref();
  const formData = reactive(createDefaultData());

  const resetFormKey = ref(0);

  const isSubmitting = ref(false);

  const isAbleSubmit = computed(() => formData.cluster_ids.length > 0 && formData.execute_sqls.length > 0);

  const handleSubmit = () => {
    formRef.value.validate();
    const executeInfo = sqlFileRef.value.getValue();
    const params = {
      bk_biz_id: currentBizId,
      details: {
        cluster_ids: formData.cluster_ids,
        ...executeInfo,
      },
      ticket_type: TicketTypes.MONGODB_EXEC_SCRIPT_APPLY,
    };

    InfoBox({
      title: t('确认执行变更脚本任务'),
      subTitle: t('该操作将会修改对应DB的数据，请谨慎操作'),
      width: 400,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params)
          .then((data) => {
            window.changeConfirm = false;
            router.push({
              name: 'MongoScriptExecute',
              params: {
                step: 'success',
              },
              query: {
                ticketId: data.id,
              },
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      },
    });
  };

  const handleReset = () => {
    resetFormKey.value = resetFormKey.value + 1;
    Object.assign(formData, createDefaultData());
  };
</script>

<style lang="less">
  .mongo-script-execute-page {
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
