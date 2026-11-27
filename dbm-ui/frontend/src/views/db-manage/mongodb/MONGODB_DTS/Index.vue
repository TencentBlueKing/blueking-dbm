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
    <div class="mongo-dts-page db-toolbox">
      <BkAlert
        class="mb-16"
        theme="info"
        :title="
          t(
            'DTS 同步：在执行机上用 MongoShake 做源→目标全量+增量同步。执行机可按规格从资源池申请、填写业务空闲机 IP，或复用已有执行机 ID；同步结束后无其它任务使用的执行机会下架回收。命名空间填库或库.表，不支持通配；留空表示同步除 admin、local、config 外的全部用户库表',
          )
        " />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
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
              :min-width="280"
              :selected="selectedSources"
              @batch-edit="handleSourceBatchEdit" />
            <TargetClusterColumn
              v-model="item.target_cluster"
              :min-width="280"
              :selected="selectedTargets"
              :source-cluster="item.source_cluster"
              @batch-edit="handleTargetBatchEdit" />
            <NamespaceColumn
              v-model="item.namespaces"
              @batch-edit="handleNamespaceBatchEdit" />
            <EditableColumn
              field="stop_mode"
              :label="t('停止方式')"
              :min-width="140"
              required>
              <BkSelect
                v-model="item.stop_mode"
                :clearable="false">
                <BkOption
                  :label="t('追平自动停')"
                  value="auto" />
                <BkOption
                  :label="t('追平后人工确认停')"
                  value="manual" />
              </BkSelect>
            </EditableColumn>
            <EditableColumn
              field="exec_host_source"
              :label="t('执行机来源')"
              :min-width="140"
              required>
              <BkSelect
                v-model="item.exec_host_source"
                :clearable="false">
                <BkOption
                  :label="t('资源池申请')"
                  value="resource" />
                <BkOption
                  :label="t('复用执行机')"
                  value="reuse" />
                <BkOption
                  :label="t('手填 IP')"
                  value="manual" />
              </BkSelect>
            </EditableColumn>
            <SpecColumn
              v-model="item.spec_id"
              :cluster-type="DBTypes.MONGODB"
              field="spec_id"
              :label="t('执行机规格')"
              :machine-type="MachineTypes.MONGODB"
              :required="item.exec_host_source === 'resource'"
              selectable />
            <EditableColumn
              field="exec_host_id"
              :label="t('执行机 ID')"
              :min-width="120"
              :required="item.exec_host_source === 'reuse'">
              <EditableInput
                v-model="item.exec_host_id"
                :disabled="item.exec_host_source !== 'reuse'"
                :placeholder="t('复用时填写')"
                type="number" />
            </EditableColumn>
            <EditableColumn
              field="exec_host_ip"
              :label="t('执行机 IP')"
              :min-width="160"
              :required="item.exec_host_source === 'manual'">
              <EditableInput
                v-model="item.exec_host_ip"
                :disabled="item.exec_host_source !== 'manual'"
                :placeholder="t('业务空闲机 IP')" />
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

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';
  import TargetClusterColumn from '@views/db-manage/mongodb/MONGODB_DATA_MIGRATE/components/TargetClusterColumn.vue';
  import NamespaceColumn from '@views/db-manage/mongodb/MONGODB_DTS/components/NamespaceColumn.vue';

  import { random } from '@utils';

  type ExecHostSource = 'manual' | 'resource' | 'reuse';

  interface IDataRow {
    exec_host_id: number | '';
    exec_host_ip: string;
    exec_host_source: ExecHostSource;
    namespaces: string[];
    source_cluster: {
      cluster_type: ClusterTypes | string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    spec_id: number;
    stop_mode: 'auto' | 'manual';
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
    exec_host_source: values.exec_host_source || ('resource' as ExecHostSource),
    namespaces: values.namespaces || [],
    source_cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.source_cluster,
    ),
    spec_id: values.spec_id || 0,
    stop_mode: values.stop_mode || ('auto' as const),
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
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  const getExecHostSource = (item: Mongodb.Dts['infos'][number]): ExecHostSource => {
    if (item.exec_host_id) {
      return 'reuse';
    }
    if (item.resource_spec?.exec_host) {
      return 'resource';
    }
    return item.exec_host?.ip ? 'manual' : 'resource';
  };

  useTicketDetail<Mongodb.Dts>(TicketTypes.MONGODB_DTS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((item) =>
          createRowData({
            exec_host_id: item.exec_host_id || '',
            // 资源池申请的单据再次提单时重新申请，不沿用已分配的 IP
            exec_host_ip: item.resource_spec?.exec_host ? '' : item.exec_host?.ip || '',
            exec_host_source: getExecHostSource(item),
            namespaces: item.namespaces || [],
            source_cluster: {
              master_domain: clusters[item.source_cluster_id].immute_domain,
            } as IDataRow['source_cluster'],
            spec_id: item.resource_spec?.exec_host?.spec_id || 0,
            stop_mode: item.stop_mode || 'auto',
            target_cluster: {
              master_domain: clusters[item.target_cluster_id].immute_domain,
            } as IDataRow['target_cluster'],
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Mongodb.Dts['infos'];
  }>(TicketTypes.MONGODB_DTS);

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
  const selectedSourceMap = computed(() =>
    Object.fromEntries(selectedSources.value.map((cur) => [cur.master_domain, true])),
  );

  const handleSubmit = async () => {
    await formRef.value!.validate();
    editableTableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableRow) => {
            const info: Mongodb.Dts['infos'][number] = {
              namespaces: tableRow.namespaces,
              recycle_exec_host: true,
              source_cluster_id: tableRow.source_cluster.id,
              source_connect_mode: 'secondaryPreferred',
              stop_mode: tableRow.stop_mode,
              target_cluster_id: tableRow.target_cluster.id,
            };
            if (tableRow.exec_host_source === 'reuse') {
              info.exec_host_id = Number(tableRow.exec_host_id);
            } else if (tableRow.exec_host_source === 'manual') {
              info.exec_host = { ip: tableRow.exec_host_ip.trim() };
            } else {
              info.resource_spec = { exec_host: { spec_id: tableRow.spec_id } };
            }
            return info;
          }),
        },
        ...formData.payload,
      });
    });
  };

  const handleNamespaceBatchEdit = (value: string[]) => {
    formData.tableData.forEach((item, index) => {
      formData.tableData[index] = {
        ...item,
        namespaces: [...value],
      };
    });
  };

  const handleSourceBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedSourceMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            source_cluster: {
              master_domain: item.master_domain,
            } as IDataRow['source_cluster'],
          }),
        );
      }
    });
    formData.tableData = [...(selectedSources.value.length ? formData.tableData : []), ...newList];
  };

  const handleTargetBatchEdit = (clusterList: MongodbModel[]) => {
    if (!clusterList.length) {
      return;
    }
    const firstEmpty = formData.tableData.find((item) => !item.target_cluster.id);
    const cluster = clusterList[0]!;
    if (firstEmpty) {
      firstEmpty.target_cluster = {
        cluster_type: cluster.cluster_type,
        cluster_type_name: cluster.cluster_type_name,
        id: cluster.id,
        master_domain: cluster.master_domain,
      };
      return;
    }
    formData.tableData.push(
      createRowData({
        target_cluster: {
          cluster_type: cluster.cluster_type,
          cluster_type_name: cluster.cluster_type_name,
          id: cluster.id,
          master_domain: cluster.master_domain,
        },
      }),
    );
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>

<style lang="less" scoped>
  .mongo-dts-page {
    padding-bottom: 20px;
  }
</style>
