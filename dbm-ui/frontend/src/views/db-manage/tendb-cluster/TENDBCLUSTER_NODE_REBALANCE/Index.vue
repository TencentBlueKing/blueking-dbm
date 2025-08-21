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
    <BkAlert
      class="mb-20"
      closable
      :title="t('集群容量变更：通过部署新集群来实现原集群的扩容或缩容（集群分片数不变）')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <CapacityColumn
            v-model="item.targetCapacity"
            :cluster="item.cluster" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.cluster.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
              spec_id: item.targetCapacity.spec_id,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BackupSource v-model="formData.backupSource" />
      <BkFormItem
        :label="t('数据校验')"
        property="need_checksum"
        required>
        <BkSwitcher
          v-model="formData.need_checksum"
          theme="primary" />
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
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
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { Affinity, DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import CapacityColumn from './components/capacity-column/Index.vue';
  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    targetCapacity: ComponentProps<typeof CapacityColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'spider.tendb-test.1.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_capacity: 0,
        cluster_shard_num: 0,
        cluster_spec: {} as TendbClusterModel['cluster_spec'],
        db_module_id: 0,
        disaster_tolerance_level: Affinity.CROS_SUBZONE,
        id: 0,
        machine_pair_cnt: 0,
        master_domain: '',
        region: '',
        remote_shard_num: 0,
      },
      data.cluster,
    ),
    labels: (data.labels || []) as RowData['labels'],
    targetCapacity: Object.assign(
      {
        cluster_capacity: 0,
        machine_pair: 0,
        spec_id: 0,
        spec_name: '',
      },
      data.targetCapacity,
    ),
  });

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    need_checksum: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  useTicketDetail<TendbCluster.ResourcePool.NodeRebalance>(TicketTypes.TENDBCLUSTER_NODE_REBALANCE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        backupSource: details.backup_source,
        need_checksum: details.need_checksum,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          return createTableRow({
            cluster: {
              master_domain: clusters[item.cluster_id]?.immute_domain || '',
            },
            labels: (item.resource_spec.backend_group.labels || []).map((item) => ({ id: Number(item) })),
            targetCapacity: {
              cluster_capacity: item.resource_spec.backend_group.futureCapacity,
              machine_pair: item.resource_spec.backend_group.count,
              spec_id: item.resource_spec.backend_group.spec_id,
              spec_name: item.resource_spec.backend_group.specName,
            },
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      bk_cloud_id: number;
      cluster_id: number;
      cluster_shard_num: number;
      db_module_id: number;
      prev_cluster_spec_name: string;
      prev_machine_pair: number;
      remote_shard_num: number;
      resource_spec: {
        backend_group: {
          affinity: string;
          count: number;
          futureCapacity: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
          specName: string;
        };
      };
      spec_id: number;
    }[];
    need_checksum: boolean;
  }>(TicketTypes.TENDBCLUSTER_NODE_REBALANCE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }

    createTicketRun({
      details: {
        backup_source: formData.backupSource,
        infos: formData.tableData.map((item) => ({
          bk_cloud_id: item.cluster.bk_cloud_id,
          cluster_id: item.cluster.id,
          cluster_shard_num: item.cluster.cluster_shard_num,
          db_module_id: item.cluster.db_module_id,
          prev_cluster_spec_name: item.cluster.cluster_spec.spec_name,
          prev_machine_pair: item.cluster.machine_pair_cnt,
          remote_shard_num: Math.ceil(item.cluster.cluster_shard_num / item.targetCapacity.machine_pair),
          resource_spec: {
            backend_group: {
              affinity: item.cluster.disaster_tolerance_level,
              count: item.targetCapacity.machine_pair,
              futureCapacity: item.targetCapacity.cluster_capacity,
              label_names: item.labels.map((item) => item.value),
              labels: item.labels.map((item) => String(item.id)),
              spec_id: item.targetCapacity.spec_id,
              specName: item.targetCapacity.spec_name,
            },
          },
          spec_id: item.cluster.cluster_spec.spec_id,
        })),
        need_checksum: formData.need_checksum,
      },
      remark: formData.payload.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          cluster: {
            master_domain: item.master_domain,
          },
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
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
