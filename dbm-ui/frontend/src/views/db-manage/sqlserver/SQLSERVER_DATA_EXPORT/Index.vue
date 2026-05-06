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
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('按指定查询SQL语句导出数据')" />
    <BkForm
      :key="formData.render_key"
      ref="form"
      class="mt-16 mb-16 toolbox-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('集群类型')"
        property="cluster_type"
        required>
        <BkRadioGroup
          v-model="formData.cluster_type"
          style="width: 300px"
          type="card"
          @change="handleClusterTypeChange">
          <BkRadioButton :label="ClusterTypes.SQLSERVER_HA">
            {{ t('主从') }}
          </BkRadioButton>
          <BkRadioButton :label="ClusterTypes.SQLSERVER_SINGLE">
            {{ t('单节点') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <ClusterFormItem
        v-model="formData.cluster_domain"
        :cluster-type="formData.cluster_type"
        @change="handleClusterChange" />
      <BkFormItem
        v-if="formData.cluster_type === ClusterTypes.SQLSERVER_HA"
        :label="t('查询角色')"
        property="role"
        required>
        <BkRadioGroup
          v-model="formData.role"
          style="width: 300px"
          type="card">
          <BkRadioButton label="master"> Master </BkRadioButton>
          <BkRadioButton label="slave"> Slave </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <DbFormItem
        v-model="formData.execute_objects"
        :validate-master="formData.role === 'master'" />
      <BkFormItem
        :label="t('查询 SQL')"
        property="sql_file"
        required>
        <SqlQuery
          ref="sqlQuery"
          :cluster-list="formData.cluster_list"
          @grammar-check="handleGrammarCheck" />
      </BkFormItem>
    </BkForm>
    <template #action>
      <span
        v-bk-tooltips="{
          content: submitButtonTips,
          disabled: !submitButtonTips,
        }">
        <BkButton
          class="w-88"
          :disabled="Boolean(submitButtonTips)"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </span>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Sqlserver } from '@services/model/ticket/ticket';
  import { batchFetchFile } from '@services/source/storage';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { random } from '@utils';

  import ClusterFormItem, { type ClusterModelMap } from './components/ClusterFormItem.vue';
  import DbFormItem from './components/DbFormItem.vue';
  import SqlQuery from './components/sql-query/Index.vue';

  type SupportClusterTypes = ComponentProps<typeof ClusterFormItem>['clusterType'];

  const { t } = useI18n();

  const formRef = useTemplateRef('form');
  const sqlQueryRef = useTemplateRef('sqlQuery');

  const defaultData = () => ({
    cluster_domain: '',
    cluster_list: {} as ClusterModelMap[SupportClusterTypes][],
    cluster_type: ClusterTypes.SQLSERVER_HA as SupportClusterTypes,
    execute_objects: [] as Sqlserver.DataExport['execute_objects'],
    render_key: random(),
    role: 'slave',
    sql_file: '',
  });

  const formData = reactive(defaultData());
  const hasGrammarCheck = ref(false);
  const grammarCheckResult = ref(false);
  const submitButtonTips = computed(() => {
    if (!hasGrammarCheck.value) {
      return t('先执行语法检测');
    }
    if (!grammarCheckResult.value) {
      return t('语法检测失败');
    }

    return '';
  });

  useTicketDetail<Sqlserver.DataExport>(TicketTypes.SQLSERVER_DATA_EXPORT, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters } = details;
      const clusterList = Object.values(clusters);
      if (clusterList.length) {
        Object.assign(formData, defaultData(), {
          cluster_domain: clusterList.map((cluster) => cluster.immute_domain).join('\n'),
          cluster_list: clusterList,
          cluster_type: clusterList[0].cluster_type,
          execute_objects: details.execute_objects,
          role: details.select_role,
        });
        batchFetchFile({
          file_path_list: [`${details.path}/${details.execute_objects[0].sql_files[0]}`],
        }).then((res) => {
          formData.sql_file = res[0].content;
          sqlQueryRef.value!.setValue(res[0].content);
        });
      }
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_ids: number[];
    execute_objects: {
      dbnames: string[];
      ignore_dbnames?: string[];
      sql_files: string[];
    }[];
    select_role?: string;
  }>(TicketTypes.SQLSERVER_DATA_EXPORT);

  const handleClusterTypeChange = (clusterType: SupportClusterTypes) => {
    Object.assign(formData, defaultData(), {
      cluster_type: clusterType,
      role: clusterType === ClusterTypes.SQLSERVER_SINGLE ? 'orphan' : 'master',
    });
  };

  const handleReset = () => {
    handleClusterTypeChange(formData.cluster_type);
  };

  const handleClusterChange = (data: ClusterModelMap[SupportClusterTypes][]) => {
    formData.cluster_list = data;
    sqlQueryRef.value?.reEdit();
  };

  // 语法检测状态
  const handleGrammarCheck = (doCheck: boolean, checkResult: boolean) => {
    hasGrammarCheck.value = doCheck;
    grammarCheckResult.value = checkResult;
  };

  const handleSubmit = async () => {
    formData.sql_file = sqlQueryRef.value!.getValue();
    const result = await formRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        cluster_ids: formData.cluster_list.map((item) => item.id),
        execute_objects: formData.execute_objects.map((item) => ({
          dbnames: item.dbnames,
          ignore_dbnames: item.ignore_dbnames,
          sql_files: [formData.sql_file],
        })),
        select_role: formData.role,
      },
    });
  };
</script>
