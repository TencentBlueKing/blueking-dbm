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
  <MigrateWrapper>
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.batchCluster"
            :selected="selected"
            :selected-map="selectedMap"
            @batch-edit="handleBatchEditCluster" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.SQLSERVER"
            :current-spec-id-list="item.batchCluster.spec_id_list"
            required
            selectable
            @batch-edit="handleBatchEdit" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEdit" />
          <AvailableResourceColumn
            :params="{
              city: generateCity(item.batchCluster.clusters),
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.SQLSERVER, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
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
  </MigrateWrapper>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import type { Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import ClusterColumn from './components/ClusterColumn.vue';
  import MigrateWrapper from './components/MigrateWrapper.vue';

  interface RowData {
    batchCluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'sqlserver.test.dba.db\\nsqlserver.test2.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '2核_4G_50G',
      key: 'spec_name',
      label: t('目标规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    batchCluster: Object.assign(
      {
        clusters: {} as RowData['batchCluster']['clusters'],
        renderText: '',
        spec_id_list: [] as RowData['batchCluster']['spec_id_list'],
      },
      data.batchCluster,
    ),
    labels: (data.labels || []) as RowData['labels'],
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() =>
    formData.tableData
      .filter((item) => item.batchCluster.renderText)
      .flatMap((item) => Object.values(item.batchCluster.clusters)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<Sqlserver.ResourcePool.ClusterMigrate>(TicketTypes.SQLSERVER_CLUSTER_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        ...createTicketPayload(ticketDetail),
        tableData: infos.map((item) => {
          const batchCluster = {
            clusters: {},
            renderText: '',
          } as RowData['batchCluster'];
          item.cluster_ids.forEach((clusterId) => {
            batchCluster.renderText += batchCluster.renderText ? '\n' : '' + clusters[clusterId].immute_domain;
          });
          const resourceSpec = item.resource_spec.new_hosts || item.resource_spec.backend_group;
          return createTableRow({
            batchCluster,
            labels: (resourceSpec?.labels || []).map((item) => ({ id: Number(item) })),
            specId: resourceSpec?.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      resource_spec: {
        [key in 'backend_group' | 'new_hosts']?: {
          // 主从集群传 backend_group、单节点集群传 new_hosts
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.SQLSERVER_CLUSTER_MIGRATE);

  const handleSubmit = () => {
    tableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => {
            const clusters = Object.values(item.batchCluster.clusters);
            return {
              cluster_ids: clusters.map((cluster) => cluster.id),
              resource_spec: clusters.reduce<
                Record<
                  string,
                  {
                    count: number;
                    label_names: string[];
                    labels: string[];
                    spec_id: number;
                  }
                >
              >((acc, cluster) => {
                Object.assign(acc, {
                  [cluster?.cluster_type === ClusterTypes.SQLSERVER_SINGLE ? 'new_hosts' : 'backend_group']: {
                    count: 1,
                    label_names: item.labels.map((item) => item.value),
                    labels: item.labels.map((item) => String(item.id)),
                    spec_id: item.specId,
                  },
                });
                return acc;
              }, {}),
            };
          }),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: SqlserverHaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            batchCluster: {
              renderText: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...formData.tableData.filter((item) => item.batchCluster.renderText), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          batchCluster: {
            renderText: item.master_domain?.replaceAll('\\n', '\n') || '',
          },
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...formData.tableData.filter((item) => item.batchCluster.renderText), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const generateCity = (clusters: Record<string, { id: number; master_domain: string; region: string }>) => {
    const cities = Object.values(clusters).map((item) => item.region);
    return cities.length ? cities.join(',') : '';
  };
</script>
