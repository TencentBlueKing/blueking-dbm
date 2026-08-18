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
          <HostColumnGroup
            v-model="item.host"
            :selected="selected"
            :selected-map="selectedMap"
            @batch-edit="handleBatchEditHost" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.SQLSERVER"
            :current-spec-id-list="[item.host.spec.id]"
            required
            selectable
            @batch-edit="handleBatchEdit" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEdit" />
          <AvailableResourceColumn
            :params="{
              city: item.host.bk_idc_city_name,
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
  import MigrateWrapper from '@views/db-manage/sqlserver/SQLSERVER_CLUSTER_MIGRATE/components/MigrateWrapper.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorHost } from './components/HostColumnGroup.vue';

  interface RowData {
    host: ComponentProps<typeof HostColumnGroup>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
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
    host: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_idc_city_name: '',
        bk_sub_zone: '',
        ip: '',
        related_instances: [],
        spec: {
          id: 0,
        },
      } as unknown as RowData['host'],
      data.host,
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

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Sqlserver.ResourcePool.HostMigrate>(TicketTypes.SQLSERVER_HOST_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;
      Object.assign(formData, {
        ...createTicketPayload(ticketDetail),
        tableData: infos.map((item) => {
          const resourceSpec = item.resource_spec.new_hosts || item.resource_spec.backend_group;
          return createTableRow({
            host: {
              ip: item.origin_ip.ip,
            },
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
      origin_ip: {
        bk_host_id: number;
        ip: string;
      };
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
  }>(TicketTypes.SQLSERVER_HOST_MIGRATE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => {
          return {
            cluster_ids: item.host.related_instances.map((inst) => inst.cluster_id),
            origin_ip: {
              bk_host_id: item.host.bk_host_id,
              ip: item.host.ip,
            },
            related_cluster_infos: item.host.related_instances.map((instance) => ({
              cluster_id: instance.cluster_id,
              instance_address: instance.instance_address,
              master_domain: instance.master_domain,
            })),
            resource_spec: item.host.related_instances.reduce<
              Record<
                string,
                {
                  count: number;
                  label_names: string[];
                  labels: string[];
                  spec_id: number;
                }
              >
            >((acc, inst) => {
              Object.assign(acc, {
                [inst?.cluster_type === ClusterTypes.SQLSERVER_SINGLE ? 'new_hosts' : 'backend_group']: {
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
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditHost = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
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
          host: {
            ip: item.ip,
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
      formData.tableData = [...formData.tableData.filter((item) => item.host.ip), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };
</script>
