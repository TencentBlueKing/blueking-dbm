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
    <div class="mongo-dts-cleanup-page db-toolbox">
      <BkAlert
        class="mb-16"
        theme="warning"
        :title="t('DTS 清理：针对失败的 DTS 流程，停止 collector、删除临时账号并按需回收执行机。需填写失败流程的 root_id')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <DbFormItem
          :label="t('失败 DTS root_id')"
          property="source_root_id"
          required>
          <BkInput
            v-model="formData.source_root_id"
            :placeholder="t('14 位十六进制 root_id')" />
        </DbFormItem>
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.source_cluster"
              field="source_cluster.master_domain"
              :label="t('源集群')"
              :selected="selectedSources" />
            <TargetClusterColumn
              v-model="item.target_cluster"
              :selected="selectedTargets"
              :source-cluster="item.source_cluster" />
            <EditableColumn
              field="exec_host_id"
              :label="t('执行机 ID')"
              :min-width="120"
              :required="false">
              <BkInput
                v-model="item.exec_host_id"
                type="number" />
            </EditableColumn>
            <EditableColumn
              field="exec_host_ip"
              :label="t('执行机 IP')"
              :min-width="160"
              :required="false">
              <BkInput v-model="item.exec_host_ip" />
            </EditableColumn>
          </EditableRow>
        </EditableTable>
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';
  import TargetClusterColumn from '@views/db-manage/mongodb/MONGODB_DATA_MIGRATE/components/TargetClusterColumn.vue';

  import { random } from '@utils';

  interface IDataRow {
    exec_host_id?: number | '';
    exec_host_ip: string;
    source_cluster: {
      cluster_type: ClusterTypes | string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    target_cluster: {
      cluster_type: ClusterTypes | string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    exec_host_id: values.exec_host_id ?? '',
    exec_host_ip: values.exec_host_ip || '',
    source_cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.source_cluster,
    ),
    target_cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.target_cluster,
    ),
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    source_root_id: '',
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.DtsCleanup>(TicketTypes.MONGODB_DTS_CLEANUP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      const row = infos[0];
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        source_root_id: details.source_root_id || row?.source_root_id || '',
        tableData: [
          createRowData({
            exec_host_id: row?.exec_host_id || '',
            exec_host_ip: row?.exec_host?.ip || '',
            source_cluster: {
              master_domain: clusters[row.source_cluster_id].immute_domain,
            } as IDataRow['source_cluster'],
            target_cluster: {
              master_domain: clusters[row.target_cluster_id].immute_domain,
            } as IDataRow['target_cluster'],
          }),
        ],
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Mongodb.DtsCleanup['infos'];
    source_root_id: string;
  }>(TicketTypes.MONGODB_DTS_CLEANUP);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());
  const formData = reactive(createDefaultFormData());

  const selectedSources = computed(() =>
    formData.tableData.filter((item) => item.source_cluster.id).map((item) => item.source_cluster),
  );
  const selectedTargets = computed(() =>
    formData.tableData.filter((item) => item.target_cluster.id).map((item) => item.target_cluster),
  );

  const handleSubmit = async () => {
    await formRef.value!.validate();
    editableTableRef.value!.validate().then(() => {
      const tableRow = formData.tableData[0]!;
      const info: Mongodb.DtsCleanup['infos'][number] = {
        recycle_exec_host: true,
        source_cluster_id: tableRow.source_cluster.id,
        source_root_id: formData.source_root_id.trim(),
        target_cluster_id: tableRow.target_cluster.id,
      };
      const execHostId = Number(tableRow.exec_host_id);
      if (execHostId) {
        info.exec_host_id = execHostId;
      } else if (tableRow.exec_host_ip.trim()) {
        info.exec_host = { ip: tableRow.exec_host_ip.trim() };
      }
      createTicketRun({
        details: {
          infos: [info],
          source_root_id: formData.source_root_id.trim(),
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>

<style lang="less" scoped>
  .mongo-dts-cleanup-page {
    padding-bottom: 20px;
  }
</style>
