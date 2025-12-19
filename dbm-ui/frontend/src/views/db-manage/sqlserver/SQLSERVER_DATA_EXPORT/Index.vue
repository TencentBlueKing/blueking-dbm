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
        v-model:cluster-domain="formData.cluster_domain"
        v-model:cluster-ids="formData.cluster_ids"
        v-model:cluster-map="formData.cluster_map"
        :cluster-type="formData.cluster_type" />
      <BkFormItem
        v-if="formData.cluster_type === ClusterTypes.SQLSERVER_HA"
        :label="t('查询角色')"
        property="role"
        required>
        <BkRadioGroup
          v-model="formData.role"
          style="width: 300px"
          type="card">
          <BkRadioButton label="backend_master"> Master </BkRadioButton>
          <BkRadioButton label="backend_slave"> Slave </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <DbFormItem
        v-model="formData.dbname"
        :cluster-ids="formData.cluster_ids"
        :cluster-map="formData.cluster_map"
        :validate-master="formData.role === 'master'" />
      <BkFormItem
        :label="t('查询 SQL')"
        property="sql"
        required>
        <SqlQuery ref="sqlQuery" />
      </BkFormItem>
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

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { random } from '@utils';

  import ClusterFormItem from './components/ClusterFormItem.vue';
  import DbFormItem from './components/DbFormItem.vue';
  import SqlQuery from './components/sql-query/Index.vue';

  type SupportClusterTypes = ComponentProps<typeof ClusterFormItem>['clusterType'];

  const { t } = useI18n();

  const formRef = useTemplateRef('form');
  const sqlQueryRef = useTemplateRef('sqlQuery');

  const defaultData = () => ({
    cluster_domain: '',
    cluster_ids: [],
    cluster_map: {} as Record<string, string>,
    cluster_type: ClusterTypes.SQLSERVER_HA as SupportClusterTypes,
    dbname: '',
    render_key: random(),
    role: 'backend_master',
    sql: '',
  });

  const formData = reactive(defaultData());

  useTicketDetail<Sqlserver.DataExport>(TicketTypes.SQLSERVER_DATA_EXPORT, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters } = details;
      const clusterList = Object.values(clusters);
      if (clusterList.length) {
        Object.assign(formData, defaultData(), {
          cluster_domain: clusterList.map((cluster) => cluster.immute_domain).join('\n'),
          cluster_ids: clusterList.map((cluster) => cluster.id),
          cluster_map: Object.fromEntries(clusterList.map((item) => [item.id, item.master_domain])),
          cluster_type: clusterList[0].cluster_type,
          dbname: details.execute_objects[0].dbnames[0],
          role: details.select_role,
          sql: details.execute_objects[0].sql,
        });
        setTimeout(() => {
          sqlQueryRef.value!.setValue(formData.sql);
        }, 60);
      }
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_ids: number[];
    execute_objects: {
      dbnames: string[];
      sql: string;
    }[];
    select_role?: string;
  }>(TicketTypes.SQLSERVER_DATA_EXPORT);

  const handleClusterTypeChange = (clusterType: SupportClusterTypes) => {
    Object.assign(formData, defaultData(), {
      cluster_type: clusterType,
      role: clusterType === ClusterTypes.SQLSERVER_SINGLE ? 'orphan' : 'backend_master',
    });
  };

  const handleReset = () => {
    handleClusterTypeChange(formData.cluster_type);
  };

  const handleSubmit = async () => {
    formData.sql = sqlQueryRef.value!.getValue();
    const result = await formRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        cluster_ids: formData.cluster_ids,
        execute_objects: [
          {
            dbnames: [formData.dbname],
            sql: formData.sql,
          },
        ],
        select_role: formData.role,
      },
    });
  };
</script>
