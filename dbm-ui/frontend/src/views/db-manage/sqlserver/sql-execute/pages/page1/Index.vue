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
  <BkLoading :loading="isEditLoading">
    <SmartAction>
      <div class="sqlserver-sql-execute-page">
        <TaskTips :db-type="DBTypes.SQLSERVER" />
        <DbForm
          :key="resetFormKey"
          ref="formRef"
          form-type="vertical"
          :model="formData">
          <ClusterIds
            v-model="formData.cluster_ids"
            v-model:cluster-version-list="clusterVersionList"
            :cluster-type-list="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]" />
          <ExecuteObjects
            v-model="formData.execute_objects"
            :cluster-version-list="clusterVersionList"
            :db-type="DBTypes.SQLSERVER"
            style="margin-top: 16px"
            :upload-file-path="uploadFilePath" />
          <RenderCharset v-model="formData.charset" />
          <Backup v-model="formData.backup" />
          <TicketMode v-model="formData.ticket_mode" />
          <TicketRemark v-model="remark" />
        </DbForm>
      </div>
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="ml8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { querySemanticData } from '@services/source/mysqlSqlImport';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import TicketRemark from '@components/ticket-remark/Index.vue';

  import Backup from '@views/db-manage/common/sql-execute/backup/Index.vue';
  import RenderCharset from '@views/db-manage/common/sql-execute/charset/Index.vue';
  import ClusterIds from '@views/db-manage/common/sql-execute/cluster-ids/Index.vue';
  import ExecuteObjects from '@views/db-manage/common/sql-execute/sqlserver-execute-objects/Index.vue';
  import TaskTips from '@views/db-manage/common/sql-execute/task-tips/Index.vue';
  import TicketMode from '@views/db-manage/common/sql-execute/ticket-mode/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { rootId } = route.query as { rootId: string | undefined };

  const createDefaultData = () => ({
    charset: 'GBK',
    cluster_ids: [],
    execute_objects: [],
    backup: [],
    ticket_mode: {
      mode: 'manual',
      trigger_time: '',
    },
  });

  const formRef = ref();
  const resetFormKey = ref(0);
  const isSubmitting = ref(false);
  const uploadFilePath = ref('');
  const clusterVersionList = ref<string[]>([]);
  const remark = ref('');

  const formData = reactive(createDefaultData());

  useTicketCloneInfo({
    type: TicketTypes.SQLSERVER_IMPORT_SQLFILE,
    onSuccess(cloneData) {
      Object.assign(formData, {
        charset: cloneData.charset,
        cluster_ids: cloneData.cluster_ids,
        execute_objects: cloneData.execute_objects,
        backup: cloneData.backup,
        ticket_mode: cloneData.ticket_mode,
      });
      remark.value = cloneData.remark;
      uploadFilePath.value = cloneData.path;
    },
  });

  // 模拟执行日志重新修改
  const { loading: isEditLoading } = useRequest(querySemanticData, {
    defaultParams: [
      {
        root_id: rootId as string,
      },
    ],
    manual: !rootId,
    onSuccess(semanticData) {
      Object.assign(formData, {
        charset: semanticData.charset,
        cluster_ids: semanticData.cluster_ids,
        execute_objects: semanticData.execute_objects,
        backup: semanticData.backup,
        ticket_mode: semanticData.ticket_mode,
      });
      uploadFilePath.value = semanticData.path;
    },
  });

  // 开始模拟执行
  const handleSubmit = () => {
    isSubmitting.value = true;

    formRef.value
      .validate()
      .then(() =>
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          ticket_type: TicketTypes.SQLSERVER_IMPORT_SQLFILE,
          remark: remark.value,
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
