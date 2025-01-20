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
    <div class="install-module">
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
          class="mt16 mb16"
          :model="formData.tableData"
          :rules="rules">
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
              :params="{
                clusterId: item.cluster.id,
                version: item.cluster.major_version,
              }">
            </ModuleSelectColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData" />
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
  import type { ComponentProps } from 'vue-component-type-helpers';
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
      id: number;
      master_domain: string;
      bk_cloud_id: number;
      cluster_type: string;
      cluster_type_name: string;
      major_version: string;
    };
    load_modules: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
        bk_cloud_id: 0,
        cluster_type: '',
        cluster_type_name: '',
        major_version: '',
      },
      values.cluster,
    ),
    load_modules: values?.load_modules || [],
  });

  const createDefaultFormData = () => ({
    tableData: [createRowData()],
    data_check_repair_setting_type: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
    data_check_repair_setting_execution_frequency: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
    ...createTickePayload(),
  });

  const { t } = useI18n();

  // 单据克隆
  useTicketDetail<Redis.InstallModule>(TicketTypes.REDIS_CLUSTER_LOAD_MODULES, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;
      Object.assign(formData, {
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            load_modules: infoItem.load_modules,
          }),
        ),
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    bk_cloud_id: number;
    infos: {
      cluster_id: number;
      db_version: string;
      load_modules: string[];
    }[];
  }>(TicketTypes.REDIS_CLUSTER_LOAD_MODULES);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = formData.tableData.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
  };

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.REDIS_INSTANCE].join(','),
          ...params,
        }),
    },
  } as unknown as Record<string, TabItem>;

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterColumn>['selected'] = {
      [ClusterTypes.REDIS]: [],
    };
    formData.tableData.forEach((tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id && masterDomain) {
        selectedClusters[ClusterTypes.REDIS].push({
          id,
          master_domain: masterDomain,
        });
      }
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        const domain = item.master_domain;
        if (!clusterMemo.value[domain]) {
          newList.push(
            createRowData({
              cluster: {
                id: item.id,
                master_domain: item.master_domain,
                bk_cloud_id: item.bk_cloud_id,
                cluster_type: item.cluster_type,
                cluster_type_name: item.cluster_type_name,
                major_version: item.major_version,
              },
            }),
          );
        }
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...newList];
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
        remark: formData.remark,
      });
    }
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .install-module {
    padding-bottom: 20px;
  }
</style>
