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
        t('将源集群中指定库表的数据与表结构导出为文件；支持整表导出，或按条件筛选记录后导出。系统库不在导出范围内。')
      " />
    <BkForm
      ref="formRef"
      class="dump-data-form mb-20"
      form-type="vertical"
      :model="formData">
      <!-- 源集群 -->
      <FormItemWithHint
        :label="t('源集群')"
        :model="formData.clusterId"
        property="clusterId"
        required>
        <ClusterSelect
          v-model="formData.clusterId"
          :cluster-types="[ClusterTypes.TENDBCLUSTER]"
          :db-type="DBTypes.TENDBCLUSTER"
          :placeholder="t('请选择源集群')" />
      </FormItemWithHint>

      <!-- 导出方式 -->
      <FormItemWithHint
        :label="t('导出方式')"
        :model="formData.exportScope"
        property="exportScope"
        required>
        <BkRadioGroup v-model="formData.exportScope">
          <BkRadio label="table">{{ t('整表导出') }}</BkRadio>
          <BkRadio label="row">{{ t('条件导出') }}</BkRadio>
        </BkRadioGroup>
      </FormItemWithHint>

      <!-- 导出物 -->
      <FormItemWithHint
        :label="t('导出物')"
        :model="formData.exportType"
        property="exportType"
        required>
        <BkRadioGroup v-model="formData.exportType">
          <BkRadio label="all">{{ t('数据和表结构') }}</BkRadio>
          <BkRadio label="data">{{ t('仅数据') }}</BkRadio>
          <BkRadio
            v-if="formData.exportScope !== 'row'"
            label="schema">
            {{ t('仅表结构') }}
          </BkRadio>
        </BkRadioGroup>
      </FormItemWithHint>

      <!-- 目标DB名 -->
      <FormItemWithHint
        :label="t('目标DB名')"
        :model="formData.databases"
        property="databases"
        required>
        <DbMultiSelect
          v-model="formData.databases"
          :cluster-id="formData.clusterId"
          :placeholder="t('请选择目标DB名')" />
      </FormItemWithHint>

      <!-- 目标表名 + 忽略表名（* 时同行） -->
      <div
        class="form-row-pair"
        :class="{ 'is-pair': isAllTablesMode }">
        <FormItemWithHint
          class="include-tables-field"
          :label="t('目标表名')"
          :model="formData.tables"
          property="tables"
          required>
          <DbTableSelect
            v-model="formData.tables"
            :cluster-id="formData.clusterId"
            :databases="formData.databases"
            mode="include"
            :multi-db-locked="isMultiDb"
            :placeholder="t('点击选择表')" />
        </FormItemWithHint>
        <BkFormItem
          v-if="isAllTablesMode"
          class="ignore-tables-field"
          :label="t('忽略表名')">
          <DbTableSelect
            v-model="formData.tablesIgnore"
            :cluster-id="formData.clusterId"
            :databases="formData.databases"
            mode="ignore"
            :placeholder="t('点击选择要排除的表')" />
        </BkFormItem>
      </div>

      <!-- where 条件（条件导出） -->
      <FormItemWithHint
        v-if="formData.exportScope === 'row'"
        :hint="t('多表共用同一条件；不带 where 关键字')"
        :label="t('where 条件')"
        :model="formData.where"
        property="where"
        required>
        <BkInput
          v-model="formData.where"
          :placeholder="t('请输入条件，例如 id between 1 and 10000')"
          :rows="3"
          type="textarea" />
      </FormItemWithHint>

      <TicketPayload
        v-model="formData.payload"
        :width="560" />
    </BkForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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

<script lang="ts" setup>
  import { computed, reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { type TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import ClusterSelect from '@views/db-manage/common/toolbox-field/cluster-select/Index.vue';
  import DbMultiSelect from '@views/db-manage/common/toolbox-field/db-multi-select/Index.vue';
  import DbTableSelect from '@views/db-manage/common/toolbox-field/db-table-select/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  type ExportScope = 'table' | 'row';
  type ExportType = 'all' | 'data' | 'schema';

  interface IFormData {
    clusterId: number;
    databases: string[];
    exportScope: ExportScope;
    exportType: ExportType;
    payload: ReturnType<typeof createTicketPayload>;
    tables: string[];
    tablesIgnore: string[];
    where: string;
  }

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const formRef = useTemplateRef('formRef');

  const defaultData = () => ({
    clusterId: route.query.clusterId ? Number(route.query.clusterId) : (undefined as unknown as number),
    databases: [] as string[],
    exportScope: 'table' as ExportScope,
    exportType: 'all' as ExportType,
    payload: createTicketPayload(),
    tables: [] as string[],
    tablesIgnore: [] as string[],
    where: '',
  });

  const formData = reactive(defaultData()) as IFormData;

  const isMultiDb = computed(() => formData.databases.length > 1);
  const isAllTablesMode = computed(() => formData.tables.length === 1 && formData.tables[0] === '*');

  // 多库时强制 tables = ['*']，清空忽略表
  watch(isMultiDb, (multi) => {
    if (multi) {
      if (!(formData.tables.length === 1 && formData.tables[0] === '*')) {
        formData.tables = ['*'];
      }
      formData.tablesIgnore = [];
    }
  });

  // 非 * 模式时清空忽略表
  watch(isAllTablesMode, (allMode) => {
    if (!allMode) {
      formData.tablesIgnore = [];
    }
  });

  // 条件导出时隐藏「仅表结构」，若当前为 schema 则切回 data
  watch(
    () => formData.exportScope,
    (scope) => {
      if (scope === 'row' && formData.exportType === 'schema') {
        formData.exportType = 'data';
      }
    },
  );

  const isApplyingTicket = ref(false);

  // 源集群切换时清空库表
  watch(
    () => formData.clusterId,
    () => {
      if (isApplyingTicket.value) return;
      formData.databases = [];
      formData.tables = [];
      formData.tablesIgnore = [];
    },
  );

  useTicketDetail<TendbCluster.DumpData>(TicketTypes.TENDBCLUSTER_DUMP_DATA, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const exportScope: ExportScope = details.where ? 'row' : 'table';
      const exportType: ExportType =
        details.dump_data && details.dump_schema ? 'all' : details.dump_data ? 'data' : 'schema';
      isApplyingTicket.value = true;
      formData.payload.remark = ticketDetail.remark;
      formData.clusterId = details.cluster_id;
      formData.databases = details.databases;
      formData.exportScope = exportScope;
      formData.exportType = exportType;
      formData.tables = details.tables;
      formData.tablesIgnore = details.tables_ignore;
      formData.where = details.where;
      // 回填完成，放行后续集群切换清空
      nextTick(() => {
        isApplyingTicket.value = false;
      });
    },
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
  }>(TicketTypes.TENDBCLUSTER_DUMP_DATA);

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
      alert(t('请至少选择 1 个目标 DB'));
      return;
    }

    if (formData.tables.length === 0) {
      alert(t('请选择目标表名'));
      return;
    }

    // 多库时目标表必须为 *
    if (isMultiDb.value && !(formData.tables.length === 1 && formData.tables[0] === '*')) {
      alert(t('多个目标库时，目标表名只能为 *'));
      return;
    }

    // 忽略表不支持 *
    if (formData.tablesIgnore.includes('*')) {
      alert(t('忽略表名不支持 *'));
      return;
    }

    // 条件导出不支持仅表结构
    if (formData.exportScope === 'row' && formData.exportType === 'schema') {
      alert(t('条件导出不支持仅导出表结构'));
      return;
    }

    // 条件导出 where 必填
    if (formData.exportScope === 'row' && !formData.where.trim()) {
      alert(t('请填写 where 条件'));
      return;
    }

    createTicketRun({
      details: {
        charset: 'default',
        cluster_id: formData.clusterId,
        databases: formData.databases,
        dump_data: formData.exportType === 'all' || formData.exportType === 'data',
        dump_schema: formData.exportType === 'all' || formData.exportType === 'schema',
        tables: formData.tables,
        tables_ignore: isAllTablesMode.value ? formData.tablesIgnore : [],
        where: formData.exportScope === 'row' ? formData.where : '',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    const data = defaultData();
    isApplyingTicket.value = false;
    Object.assign(formData, data);
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>

<style lang="less" scoped>
  .dump-data-form {
    max-width: 1136px;

    :deep(.bk-form-item) {
      .bk-select,
      .bk-input,
      .bk-textarea {
        max-width: 560px;
      }
    }

    // 覆盖 bkui-vue .bk-form-item:last-child { margin-bottom: 0 }
    .form-row-pair :deep(.bk-form-item) {
      margin-bottom: 24px;
    }

    .form-row-pair {
      display: contents;

      &.is-pair {
        display: flex;
        gap: 16px;
        align-items: flex-start;

        .include-tables-field {
          flex: 0 0 560px;
          max-width: 560px;
          min-width: 0;
        }

        .ignore-tables-field {
          flex: 1;
          max-width: 560px;
          min-width: 0;
        }
      }
    }
  }
</style>
