<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="
        t(
          '将源集群中的数据导出为文件。按库表导出支持整表或按条件导出，可带表结构；按 SQL 导出执行查询 SQL 中的 SELECT，导出查询结果。系统库不在导出范围内。',
        )
      " />
    <DbForm
      class="mb-24"
      form-type="vertical">
      <DbFormItem
        :label="t('导出模式')"
        required>
        <CardCheckbox
          v-model="exportMode"
          :desc="t('选择库表，整表或按条件导出数据与表结构')"
          :disabled="isSubmitting"
          :disabled-tooltips="t('提交中')"
          :title="t('按库表导出')"
          true-value="table" />
        <CardCheckbox
          v-model="exportMode"
          class="ml-8"
          :desc="t('输入或上传查询 SQL，导出 SELECT 的查询结果')"
          :disabled="isSubmitting"
          :disabled-tooltips="t('提交中')"
          :title="t('按 SQL 导出')"
          true-value="sql" />
      </DbFormItem>
    </DbForm>
    <BkLoading :loading="isSubmitting">
      <KeepAlive :key="resetKey">
        <Component
          :is="modeComponent"
          :key="exportMode"
          ref="modeRef"
          :db-type="dbType"
          :restore-ticket="restoreTicket" />
      </KeepAlive>
    </BkLoading>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useEventBus, useTicketDetail } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import CardCheckbox from '@views/db-manage/common/db-card-checkbox/CardCheckbox.vue';

  import SqlMode from './components/sql-mode/Index.vue';
  import TableMode from './components/table-mode/Index.vue';

  interface Props {
    dbType: DBTypes.MYSQL | DBTypes.TENDBCLUSTER;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();
  const modeRef = useTemplateRef<ComponentExposed<typeof SqlMode | typeof TableMode>>('modeRef');
  const exportMode = ref('table');
  const resetKey = ref(0);
  const restoreTicket = ref(true);
  const isPreparing = ref(false);
  const modeComponent = computed(() => (exportMode.value === 'sql' ? SqlMode : TableMode));
  const ticketType = props.dbType === DBTypes.MYSQL ? TicketTypes.MYSQL_DUMP_DATA : TicketTypes.TENDBCLUSTER_DUMP_DATA;

  useTicketDetail<Mysql.DumpData>(ticketType, {
    onSuccess({ details }) {
      if (!restoreTicket.value) return;
      exportMode.value = details.export_mode === 'sql' ? 'sql' : 'table';
    },
  });

  const { loading: ticketLoading, run: createTicketRun } = useCreateTicket<
    | {
        charset: string;
        cluster_id: number;
        databases: string[];
        dump_data: boolean;
        dump_schema: boolean;
        tables: string[];
        tables_ignore: string[];
        where: string;
      }
    | {
        charset: string;
        cluster_id: number;
        export_mode: 'sql';
        result_format: 'txt' | 'csv';
        sql_filename: string;
        sql_path: string;
      }
  >(ticketType, {
    onError(errors) {
      eventBus.emit(
        'db-toolbox-error',
        errors
          .map((item) =>
            item.field === 'sql' ? `${t('语句序号：n', { n: item.row_key })} ${item.errors}` : item.errors,
          )
          .join('\n'),
      );
    },
  });

  const isSubmitting = computed(() => isPreparing.value || ticketLoading.value);

  const handleSubmit = async () => {
    if (isSubmitting.value || !modeRef.value) return;
    const currentMode = modeRef.value;
    isPreparing.value = true;
    try {
      await currentMode.validate();
      const payload = { ...currentMode.getPayload() };
      const details = await currentMode.getValue();
      await createTicketRun({
        details,
        ...payload,
      });
    } catch (error: unknown) {
      if (error instanceof Error) {
        eventBus.emit('db-toolbox-error', error.message);
      }
    } finally {
      isPreparing.value = false;
    }
  };

  const handleReset = () => {
    restoreTicket.value = false;
    exportMode.value = 'table';
    resetKey.value += 1;
    window.changeConfirm = false;
    eventBus.emit('db-toolbox-error', '');
  };
</script>
