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
  <BkLoading :loading="isEditLoading || isEditTicketLoading">
    <SmartAction>
      <div class="tendb-sql-execute-page">
        <TaskTips :db-type="DBTypes.TENDBCLUSTER" />
        <DbForm
          :key="resetFormKey"
          ref="formRef"
          form-type="vertical"
          :model="formData">
          <ClusterIds
            v-model="formData.cluster_ids"
            v-model:cluster-version-list="clusterVersionList"
            :cluster-type-list="[ClusterTypes.TENDBCLUSTER]" />
          <ExecuteObjects
            v-model="formData.execute_objects"
            cluster-type="tendbcluster"
            :cluster-version-list="clusterVersionList"
            :db-type="DBTypes.TENDBCLUSTER"
            style="margin-top: 16px"
            :upload-file-path="uploadFilePath" />
          <RenderCharset v-model="formData.charset" />
          <Backup v-model="formData.backup" />
          <TicketMode v-model="formData.ticket_mode" />
          <TicketRemark v-model="formData.remark" />
        </DbForm>
      </div>
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('模拟执行') }}
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

  import type { MySQLImportSQLFileDetails } from '@services/model/ticket/details/mysql';
  import { querySemanticData, semanticCheck } from '@services/source/mysqlSqlImport';
  import { getTicketDetails } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import TicketRemark from '@components/ticket-remark/Index.vue';

  import Backup from '@views/db-manage/common/sql-execute/backup/Index.vue';
  import RenderCharset from '@views/db-manage/common/sql-execute/charset/Index.vue';
  import ClusterIds from '@views/db-manage/common/sql-execute/cluster-ids/Index.vue';
  import ExecuteObjects from '@views/db-manage/common/sql-execute/execute-objects/Index.vue';
  import TaskTips from '@views/db-manage/common/sql-execute/task-tips/Index.vue';
  import TicketMode from '@views/db-manage/common/sql-execute/ticket-mode/Index.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { rootId, ticket_id: ticketId } = route.query as { rootId?: string; ticket_id?: string };

  const createDefaultData = () => ({
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    is_auto_commit: true,
    charset: 'default',
    cluster_ids: [],
    execute_objects: [],
    backup: [],
    ticket_mode: {
      mode: 'manual',
      trigger_time: '',
    },
    ticket_type: TicketTypes.TENDBCLUSTER_SEMANTIC_CHECK,
    cluster_type: DBTypes.TENDBCLUSTER,
    remark: '',
  });

  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE,
    onSuccess(cloneData) {
      Object.assign(formData, cloneData);
      window.changeConfirm = true;
    },
  });

  const formRef = ref();
  const resetFormKey = ref(0);
  const isSubmitting = ref(false);
  const uploadFilePath = ref('');
  const clusterVersionList = ref<string[]>([]);

  const formData = reactive(createDefaultData());

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

  const { loading: isEditTicketLoading } = useRequest(getTicketDetails, {
    defaultParams: [
      {
        id: Number(ticketId),
      },
    ],
    manual: !ticketId,
    onSuccess(ticketData) {
      uploadFilePath.value = (ticketData.details as MySQLImportSQLFileDetails).path;
    },
  });

  const { run: runSemanticCheck } = useRequest(semanticCheck, {
    manual: true,
    onSuccess(data) {
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
    },
  });

  // 开始模拟执行
  const handleSubmit = () => {
    isSubmitting.value = true;
    formRef.value
      .validate()
      .then(() => runSemanticCheck(formData))
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
  .tendb-sql-execute-page {
    padding-bottom: 40px;

    // .bk-form-label {
    //   font-weight: bold;
    //   color: #313238;

    //   &::after {
    //     line-height: unset !important;
    //   }
    // }
  }
</style>
