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
      :title="t('数据导出：导出指定集群的数据库数据')" />
    <BkForm
      ref="formRef"
      class="dump-data-form mb-20"
      form-type="vertical"
      :model="formData">
      <!-- 源集群 -->
      <BkFormItem
        :label="t('源集群')"
        property="clusterId"
        required>
        <ClusterSelect
          v-model="formData.clusterId"
          :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
          :db-type="DBTypes.MYSQL"
          :placeholder="t('请选择源集群')" />
      </BkFormItem>

      <!-- 源 DB -->
      <BkFormItem
        :label="t('源 DB')"
        property="databases"
        required>
        <DbMultiSelect
          v-model="formData.databases"
          :cluster-id="formData.clusterId"
          :placeholder="t('请选择，最多 5 个')" />
        <div class="form-hint">{{ t('最多选择 5 个 DB；当前已选 {n} 个', { n: formData.databases.length }) }}</div>
      </BkFormItem>

      <!-- 源表 -->
      <BkFormItem
        :label="t('源表')"
        property="tables">
        <BkInput
          v-model="formData.tablesInput"
          :placeholder="t('选填。多个表名以英文逗号分隔；支持通配符 *（如 user_*）')"
          :rows="3"
          type="textarea" />
        <div class="form-hint">{{ t('不填表示导出所选 DB 下全部表') }}</div>
      </BkFormItem>

      <!-- where 条件 -->
      <BkFormItem
        :label="t('where 条件')"
        property="where">
        <BkInput
          v-model="formData.where"
          :placeholder="t('选填。例如 id between 1 and 10000，不要带 where 关键字')"
          :rows="3"
          type="textarea" />
        <div class="form-hint">{{ t('不填代表全表导出；多张表共用同一条件') }}</div>
      </BkFormItem>

      <!-- 导出类型 -->
      <BkFormItem
        :label="t('导出类型')"
        property="exportType"
        required>
        <BkRadioGroup v-model="formData.exportType">
          <BkRadio label="DATA_TABLE">{{ t('数据和表结构') }}</BkRadio>
          <BkRadio label="DATA">{{ t('数据') }}</BkRadio>
          <BkRadio label="TABLE">{{ t('表结构') }}</BkRadio>
        </BkRadioGroup>
      </BkFormItem>

      <TicketPayload v-model="formData.payload" />
    </BkForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
</template>

<script lang="ts" setup>
  import { computed, reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { type Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import ClusterSelect from '@views/db-manage/common/toolbox-field/cluster-select/Index.vue';
  import DbMultiSelect from '@views/db-manage/common/toolbox-field/db-multi-select/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  interface IFormData {
    clusterId: number;
    databases: string[];
    exportType: string;
    payload: ReturnType<typeof createTicketPayload>;
    tablesInput: string;
    where: string;
  }

  const { t } = useI18n();

  const formRef = useTemplateRef('formRef');

  const defaultData = () => ({
    clusterId: undefined as unknown as number,
    databases: [] as string[],
    exportType: 'DATA_TABLE',
    payload: createTicketPayload(),
    tablesInput: '',
    where: '',
  });

  const formData = reactive(defaultData()) as IFormData;

  useTicketDetail<Mysql.DumpData>(TicketTypes.MYSQL_DUMP_DATA, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        ...createTicketPayload(ticketDetail),
        clusterId: details.cluster_id,
        databases: details.databases,
        exportType: details.dump_data && details.dump_schema ? 'DATA_TABLE' : details.dump_data ? 'DATA' : 'TABLE',
        tablesInput: details.tables.join(','),
        where: details.where,
      });
    },
  });

  const tables = computed(() => {
    if (!formData.tablesInput) {
      return [];
    }
    return formData.tablesInput
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter(Boolean);
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    charset: string;
    cluster_id: number;
    databases: string[];
    dump_data: boolean;
    dump_schema: boolean;
    tables: string[];
    tables_ignore: string[];
    where: string;
  }>(TicketTypes.MYSQL_DUMP_DATA);

  const handleSubmit = async () => {
    const result = await formRef.value?.validate();
    if (!result) {
      return;
    }

    if (!formData.clusterId) {
      alert(t('请先选择源集群'));
      return;
    }

    if (formData.databases.length === 0) {
      alert(t('请至少选择 1 个源 DB'));
      return;
    }

    createTicketRun({
      details: {
        charset: 'default',
        cluster_id: formData.clusterId,
        databases: formData.databases,
        dump_data: formData.exportType === 'DATA' || formData.exportType === 'DATA_TABLE',
        dump_schema: formData.exportType === 'TABLE' || formData.exportType === 'DATA_TABLE',
        tables: tables.value,
        tables_ignore: [],
        where: formData.where,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>

<style lang="less" scoped>
  .dump-data-form {
    max-width: 800px;

    .form-hint {
      margin-top: 6px;
      font-size: 12px;
      color: #979ba5;
      line-height: 1.5;
    }
  }
</style>
