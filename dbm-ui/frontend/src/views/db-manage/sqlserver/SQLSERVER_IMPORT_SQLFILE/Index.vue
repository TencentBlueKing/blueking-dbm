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
  <!-- <BkLoading :loading="isEditLoading"> -->
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
          ref="executeObjectsRef"
          v-model="formData.execute_objects"
          :cluster-version-list="clusterVersionList"
          :db-type="DBTypes.SQLSERVER"
          style="margin-top: 16px"
          :upload-file-path="uploadFilePath" />
        <RenderCharset v-model="formData.charset" />
        <Backup
          ref="backupRef"
          v-model="formData.backup" />
        <TicketMode v-model="formData.ticket_mode" />
        <TicketPayload v-model="formData.payload" />
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
  <!-- </BkLoading> -->
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import RenderCharset from '@views/db-manage/common/sql-execute/charset/Index.vue';
  import ClusterIds from '@views/db-manage/common/sql-execute/cluster-ids/Index.vue';
  import TaskTips from '@views/db-manage/common/sql-execute/task-tips/Index.vue';
  import TicketMode from '@views/db-manage/common/sql-execute/ticket-mode/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { utcDisplayTime } from '@utils';

  import Backup from './components/backup/Index.vue';
  import ExecuteObjects from './components/execute-objects/Index.vue';

  const { t } = useI18n();

  // const { rootId } = route.query as { rootId: string | undefined };

  const createDefaultData = () => ({
    backup: [] as Sqlserver.ImportSqlFile['backup'],
    charset: 'GBK',
    cluster_ids: [] as Sqlserver.ImportSqlFile['cluster_ids'],
    execute_objects: [] as Sqlserver.ImportSqlFile['execute_objects'],
    payload: createTickePayload(),
    ticket_mode: {
      mode: 'manual',
      trigger_time: '',
    },
  });

  const formRef = useTemplateRef('formRef');
  const executeObjectsRef = useTemplateRef('executeObjectsRef');
  const backupRef = useTemplateRef('backupRef');

  const resetFormKey = ref(0);
  const uploadFilePath = ref('');
  const clusterVersionList = ref<string[]>([]);

  const formData = reactive(createDefaultData());

  useTicketDetail<Sqlserver.ImportSqlFile>(TicketTypes.SQLSERVER_IMPORT_SQLFILE, {
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
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup: {
      backup_dbs: string[];
      backup_on: string;
      ignore_backup_dbs: string[];
    }[];
    charset: string;
    cluster_ids: number[];
    execute_objects: {
      dbnames: string[];
      ignore_dbnames: string[];
      import_mode: string;
      sql_files: string[];
    }[];
    ticket_mode: {
      mode: string;
      trigger_time: string;
    };
  }>(TicketTypes.SQLSERVER_IMPORT_SQLFILE);

  // 模拟执行日志重新修改
  // const { loading: isEditLoading } = useRequest(querySemanticData, {
  //   defaultParams: [
  //     {
  //       root_id: rootId as string,
  //     },
  //   ],
  //   manual: !rootId,
  //   onSuccess(semanticData) {
  //     Object.assign(formData, {
  //       backup: semanticData.backup,
  //       charset: semanticData.charset,
  //       cluster_ids: semanticData.cluster_ids,
  //       execute_objects: semanticData.execute_objects,
  //       ticket_mode: semanticData.ticket_mode,
  //     });
  //     uploadFilePath.value = semanticData.path;
  //   },
  // });

  const handleSubmit = () => {
    Promise.all([
      formRef.value!.validate(),
      executeObjectsRef.value!.validate(),
      backupRef.value ? backupRef.value!.validate() : Promise.resolve(true),
    ]).then(() =>
      createTicketRun({
        details: formData,
        ...formData.payload,
      }),
    );
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
