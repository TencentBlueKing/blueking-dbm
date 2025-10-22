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
  <ProxyWrapper>
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
            @batch-edit="handleBatchEdit" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.MYSQL"
            :machine-type="MachineTypes.MYSQL_PROXY"
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.batchCluster.cities.join(','),
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.MYSQL, 'PUBLIC'],
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
  </ProxyWrapper>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ProxyWrapper from '@views/db-manage/mysql/MYSQL_PROXY_ADD/components/ProxyWrapper.vue';

  import { random } from '@utils';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    batchCluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    batchCluster: Object.assign(
      {
        cities: [],
        clusters: [],
        renderText: '',
        spec_id_list: [],
      } as RowData['batchCluster'],
      data.batchCluster,
    ),
    labels: (data.labels || []) as RowData['labels'],
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db\\ntendbha.test2.dba.db',
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

  const selected = computed(() => formData.tableData.flatMap((item) => Object.values(item.batchCluster.clusters)));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<Mysql.ResourcePool.ProxyMigrate>(TicketTypes.MYSQL_PROXY_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      tableKey.value = random();
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          return createTableRow({
            batchCluster: {
              clusters: item.cluster_ids.map(
                (clusterId) =>
                  ({
                    master_domain: clusters[clusterId]?.immute_domain || '',
                  }) as unknown as TendbhaModel,
              ),
            },
            labels: (item.resource_spec.target_proxies?.labels || []).map((item) => ({ id: Number(item) })),
            specId: item.resource_spec.target_proxies?.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      old_nodes: {
        proxy: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          spec: TendbhaModel['proxies'][0]['spec_config'];
        }[];
      };
      origin_proxies: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        spec: TendbhaModel['proxies'][number]['spec_config'];
      }[];
      related_instances: {
        cluster_id: number;
        instance_address: string[];
      }[];
      resource_spec: {
        target_proxies: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_PROXY_MIGRATE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => {
          const proxies = _.uniqBy(
            item.batchCluster.clusters
              .flatMap((cluster) => cluster.proxies)
              .map((instance) => ({
                bk_biz_id: instance.bk_biz_id,
                bk_cloud_id: instance.bk_cloud_id,
                bk_host_id: instance.bk_host_id,
                ip: instance.ip,
                spec: instance.spec_config,
              })),
            (item) => item.ip,
          );

          return {
            cluster_ids: item.batchCluster.clusters.map((cluster) => cluster.id),
            old_nodes: {
              proxy: proxies,
            },
            origin_proxies: proxies,
            related_instances: item.batchCluster.clusters.flatMap((cluster) => ({
              cluster_id: cluster.id,
              instance_address: cluster.proxies.map((proxy) => `${proxy.ip}:${proxy.port}`),
            })),
            resource_spec: {
              target_proxies: {
                count: proxies.length,
                label_names: item.labels.map((item) => item.value),
                labels: item.labels.map((item) => String(item.id)),
                spec_id: item.specId,
              },
            },
          };
        }),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            batchCluster: {
              clusters: [item],
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [
      ...(formData.tableData[0].batchCluster.clusters.length ? formData.tableData : []),
      ...dataList,
    ];
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
      formData.tableData = [
        ...(formData.tableData[0].batchCluster.clusters.length ? formData.tableData : []),
        ...dataList,
      ]; // 追加
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };
</script>
