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
      <div class="mysql-sql-execute-page">
        <TaskTips :db-type="DBTypes.MYSQL" />
        <DbForm
          :key="resetFormKey"
          ref="formRef"
          form-type="vertical"
          :model="formData">
          <ClusterIds
            v-model="formData.cluster_ids"
            v-model:cluster-version-list="clusterVersionList"
            :cluster-type-list="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]" />
          <ExecuteObjects
            ref="executeObjectsRef"
            v-model="formData.execute_objects"
            class="mt-16"
            :cluster-ids="formData.cluster_ids"
            :cluster-type="DBTypes.MYSQL"
            :cluster-version-list="clusterVersionList"
            :upload-file-path="uploadFilePath" />
          <RenderCharset v-model="formData.charset" />
          <Backup v-model="formData.backup" />
          <TicketMode v-model="formData.ticket_mode" />
          <TicketPayload v-model="formData.payload" />
        </DbForm>
      </div>
      <template #action>
        <BkButton
          class="w-88"
          theme="primary"
          @click="handleSubmit">
          {{ t('模拟执行') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton class="ml-8 w-88">
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

  import { type Mysql } from '@services/model/ticket/ticket';
  import { querySemanticData, semanticCheck } from '@services/source/mysqlSqlImport';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import ExecuteObjects from '@views/db-manage/common/mysql-sql-execute/execute-objects/Index.vue';
  import Backup from '@views/db-manage/common/sql-execute/backup-new/Index.vue';
  import RenderCharset from '@views/db-manage/common/sql-execute/charset/Index.vue';
  import ClusterIds from '@views/db-manage/common/sql-execute/cluster-ids/Index.vue';
  import TaskTips from '@views/db-manage/common/sql-execute/task-tips/Index.vue';
  import TicketMode from '@views/db-manage/common/sql-execute/ticket-mode/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { utcDisplayTime } from '@utils';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const { rootId } = route.query as { rootId: string | undefined };

  const createDefaultData = () => ({
    backup: [] as Mysql.ImportSqlFile['backup'],
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    charset: 'default',
    cluster_ids: [] as number[],
    cluster_type: DBTypes.MYSQL,
    execute_objects: [] as Mysql.ImportSqlFile['execute_objects'],
    is_auto_commit: true,
    payload: createTickePayload(),
    ticket_mode: {
      mode: 'manual',
      trigger_time: '',
    },
    ticket_type: TicketTypes.MYSQL_SEMANTIC_CHECK,
  });

  const formRef = useTemplateRef('formRef');
  const executeObjectsRef = useTemplateRef('executeObjectsRef');

  const resetFormKey = ref(0);
  const uploadFilePath = ref('');
  const clusterVersionList = ref<string[]>([]);

  const formData = reactive(createDefaultData());

  useTicketDetail<Mysql.ImportSqlFile>(TicketTypes.MYSQL_IMPORT_SQLFILE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        backup: details.backup,
        charset: details.charset,
        cluster_ids: details.cluster_ids,
        execute_objects: details.execute_objects,
        payload: createTickePayload(ticketDetail),
        ticket_mode: {
          ...details.ticket_mode,
          trigger_time: utcDisplayTime(details.ticket_mode.trigger_time),
        },
      });
      uploadFilePath.value = details.path;
      window.changeConfirm = true;

      nextTick(() => {
        executeObjectsRef.value!.setReEditValue(details.execute_objects);
      });
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
        backup: semanticData.backup,
        charset: semanticData.charset,
        cluster_ids: semanticData.cluster_ids,
        execute_objects: semanticData.execute_objects,
        payload: createTickePayload(semanticData),
        ticket_mode: {
          ...semanticData.ticket_mode,
          trigger_time: utcDisplayTime(semanticData.ticket_mode.trigger_time),
        },
      });
      uploadFilePath.value = semanticData.path;
      window.changeConfirm = true;

      nextTick(() => {
        executeObjectsRef.value!.setReEditValue(semanticData.execute_objects);
      });
    },
  });

  const { runAsync: runSemanticCheck } = useRequest(semanticCheck, {
    manual: true,
    onSuccess(data) {
      window.changeConfirm = false;
      router.push({
        name: TicketTypes.MYSQL_IMPORT_SQLFILE,
        params: {
          step: 'log',
        },
        query: {
          nodeId: data.node_id,
          rootId: data.root_id,
        },
      });
    },
  });

  // 开始模拟执行
  const handleSubmit = () => {
    formRef.value!.validate().then(() => {
      const { payload, ...restFormData } = formData;
      runSemanticCheck({
        ...restFormData,
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    resetFormKey.value = resetFormKey.value + 1;
    Object.assign(formData, createDefaultData());
  };
</script>

<style lang="less">
  .mysql-sql-execute-page {
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
