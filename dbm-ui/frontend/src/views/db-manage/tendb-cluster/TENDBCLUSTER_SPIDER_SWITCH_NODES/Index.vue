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
  <SpiderWrapper>
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :handle-row-merge="handleRowMerge"
            :role-rowspan="item.same_role"
            :rowspan="item.same_cluster"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <SpecColumn
            v-model="item.host.spec.id"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            field="host.spec.id"
            :machine-type="MachineTypes.TENDBCLUSTER_PROXY"
            required
            :rowspan="item.same_spec" />
          <ResourceTagColumn
            v-model="item.labels"
            :rowspan="item.same_cluster"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.host.bk_idc_city_name,
              subzones: item.host.bk_sub_zone,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.host.spec.id,
              labels: item.labels.map((item) => item.id).join(','),
            }"
            :rowspan="item.same_cluster" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow"
            :handle-row-merge="handleRowMerge" />
        </EditableRow>
      </EditableTable>
      <BkFormItem>
        <BkCheckbox
          v-model="formData.is_safe"
          :false-label="false"
          true-label>
          <span
            v-bk-tooltips="t('存在业务连接时需要人工确认')"
            class="safe-action-text">
            {{ t('检查业务连接') }}
          </span>
        </BkCheckbox>
      </BkFormItem>
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
          class="ml8"
          :confirm-handler="handleReset"
          :disabled="isSubmitting" />
      </template>
    </SmartAction>
  </SpiderWrapper>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import SpiderWrapper from '@views/db-manage/tendb-cluster/TENDBCLUSTER_SPIDER_ADD_NODES/components/SpiderWrapper.vue';

  import { random } from '@utils';

  import HostColumn, { type SelectorHost, type SpecConfig } from './components/HostColumnGroup.vue';

  interface RowData {
    host: ComponentProps<typeof HostColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    same_cluster: number;
    same_role: number;
    same_spec: number;
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
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
        cluster_id: 0,
        instance_address: '',
        ip: '',
        master_domain: '',
        port: 0,
        role: '',
        spec: {
          id: 0,
        } as SpecConfig,
      },
      data.host,
    ),
    labels: (data.labels || []) as RowData['labels'],
    same_cluster: data.same_cluster || 1,
    same_role: data.same_role || 1,
    same_spec: data.same_spec || 1,
  });

  const defaultData = () => ({
    is_safe: true,
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  // 具备完全相同的集群id列的行数组map
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};
  // 相同集群id，相同role的行数组map
  let sameRoleRowsMap: Record<string, RowData[]> = {};

  // 行合并
  const handleRowMerge = () => {
    // 接口都响应后再合并
    const isRespsoned = formData.tableData.every((item) => !!item.host.cluster_id);
    if (!isRespsoned) {
      return;
    }

    const sortedData = _.sortBy(formData.tableData, [(item) => item.host.cluster_id, (item) => item.host.role]);

    sameClusterIdsRowsMap = _.groupBy(sortedData, (item) => item.host.cluster_id);
    sameRoleRowsMap = _.groupBy(sortedData, (item) => `${item.host.cluster_id}-${item.host.role}`);

    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      const isSameSpecId = list.every((item) => item.host.spec.id === list[0].host.spec.id);
      Object.assign(list[0], {
        same_cluster: list.length,
        same_spec: isSameSpecId ? list.length : 1, // 同集群下所有主机都是同一规格才合并
      });
    });
    Object.values(sameRoleRowsMap).forEach((list) => {
      Object.assign(list[0], {
        same_role: list.length,
      });
    });

    formData.tableData = sortedData;
  };

  const rules = {
    'host.role': [
      {
        message: t('同集群不允许同时操作 Spider Master 和 Spider Slave'),
        trigger: 'blur',
        validator: (
          value: string,
          row: {
            rowData: RowData;
            rowIndex: number;
          },
        ) => sameClusterIdsRowsMap[row.rowData.host.cluster_id].every((item) => item.host.role === value),
      },
    ],
    'host.spec.id': [
      {
        message: t('主机规格不一致'),
        trigger: 'blur',
        validator: (
          value: number,
          row: {
            rowData: RowData;
            rowIndex: number;
          },
        ) => sameClusterIdsRowsMap[row.rowData.host.cluster_id].every((item) => item.host.spec.id === value),
      },
    ],
  };

  useTicketDetail<TendbCluster.ResourcePool.SpiderSwitchNodes>(TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.reduce<RowData[]>((acc, item) => {
          item.spider_old_ip_list.forEach((host) => {
            acc.push(
              createTableRow({
                host: {
                  ip: host.ip,
                },
                labels: (item.resource_spec[item.switch_spider_role]!.labels || []).map((item) => ({
                  id: Number(item),
                })),
              }),
            );
          });
          return acc;
        }, []),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      old_nodes: {
        [x in string]: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      resource_spec: {
        [x in string]: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
      spider_old_ip_list: {
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        spec: SpecConfig;
      }[];
      switch_spider_role: string;
    }[];
    ip_source: 'resource_pool';
    is_safe: boolean;
  }>(TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const generateHostInfo = (data: RowData['host']) => ({
      bk_cloud_id: data.bk_cloud_id,
      bk_host_id: data.bk_host_id,
      ip: data.ip,
    });
    const generateSpecInfo = (data: RowData[]) => ({
      count: data.length,
      label_names: data[0].labels.map((item) => item.value),
      labels: data[0].labels.map((item) => String(item.id)),
      spec_id: data[0].host.spec.id,
    });
    createTicketRun({
      details: {
        infos: Object.values(sameClusterIdsRowsMap).map((rows) => {
          const masters = rows.filter((item) => item.host.role === 'spider_master');
          const slaves = rows.filter((item) => item.host.role === 'spider_slave');
          const hostList = slaves.length > 0 ? slaves : masters;
          const currentRole = hostList[0].host.role;
          return {
            cluster_id: rows[0].host.cluster_id,
            old_nodes: {
              [currentRole]: hostList.map((item) => generateHostInfo(item.host)),
            },
            resource_spec: {
              [currentRole]: generateSpecInfo(hostList),
            },
            spider_old_ip_list: hostList.map((item) => ({
              bk_cloud_id: item.host.bk_cloud_id,
              bk_host_id: item.host.bk_host_id,
              ip: item.host.ip,
              spec: item.host.spec,
            })),
            switch_spider_role: currentRole,
          };
        }),
        ip_source: 'resource_pool',
        is_safe: formData.is_safe,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: SelectorHost[]) => {
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

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        host: {
          ip: item.ip,
        },
        labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0]!.host.bk_host_id ? formData.tableData : []), ...dataList];
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

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
