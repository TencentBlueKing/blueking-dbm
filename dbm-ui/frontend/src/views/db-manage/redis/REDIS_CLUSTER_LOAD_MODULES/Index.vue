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
    <div class="pb-20">
      <BkAlert
        closable
        theme="info"
        :title="t('为集群安装扩展 Module，仅 RedisCluster、Redis 主从 支持安装 Module。')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.REDIS]"
              field="cluster.master_domain"
              :label="t('目标集群')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('架构版本')"
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('版本')"
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.major_version }}
              </EditableBlock>
            </EditableColumn>
            <ModuleSelectColumn
              v-model="item.load_modules"
              :cluster-id="item.cluster.id"
              :version="item.cluster.major_version">
            </ModuleSelectColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { RepairAndVerifyFrequencyModes, RepairAndVerifyModes } from '@services/model/redis/redis-dst-history-job';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { messageError } from '@utils';

  import ModuleSelectColumn from './components/ModuleSelectColumn.vue';

  interface IDataRow {
    cluster: {
      bk_cloud_id: number;
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      major_version: string;
      master_domain: string;
    };
    load_modules: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        major_version: '',
        master_domain: '',
      },
      values.cluster,
    ),
    load_modules: values?.load_modules || [],
  });

  const createDefaultFormData = () => ({
    data_check_repair_setting_execution_frequency: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
    data_check_repair_setting_type: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  // 单据克隆
  useTicketDetail<Redis.InstallModule>(TicketTypes.REDIS_CLUSTER_LOAD_MODULES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            load_modules: infoItem.load_modules,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    bk_cloud_id: number;
    infos: {
      cluster_id: number;
      db_version: string;
      load_modules: string[];
    }[];
  }>(TicketTypes.REDIS_CLUSTER_LOAD_MODULES);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.REDIS_INSTANCE].join(','),
          ...params,
        }),
    },
  } as unknown as Record<string, TabItem>;

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      const isSameCloud = formData.tableData.every(
        (item) => item.cluster.bk_cloud_id === formData.tableData[0].cluster.bk_cloud_id,
      );
      if (!isSameCloud) {
        messageError(t('仅允许同一管控区域的集群一起安装module'));
        return;
      }
      createTicketRun({
        details: {
          bk_cloud_id: formData.tableData[0].cluster.bk_cloud_id,
          infos: formData.tableData.map((tableItem) => ({
            cluster_id: tableItem.cluster.id,
            db_version: tableItem.cluster.major_version,
            load_modules: tableItem.load_modules,
          })),
        },
        ...formData.payload,
      });
    }
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>
