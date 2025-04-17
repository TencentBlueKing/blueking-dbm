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
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
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
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BackupSource v-model="formData.backup_source" />
      <BkFormItem
        :label="t('数据校验')"
        property="need_checksum"
        required>
        <BkSwitcher
          v-model="formData.need_checksum"
          theme="primary" />
      </BkFormItem>
      <template v-if="formData.need_checksum">
        <BkFormItem
          :label="t('校验时间')"
          property="trigger_checksum_type"
          required>
          <BkRadioGroup v-model="formData.trigger_checksum_type">
            <BkRadio label="now">
              {{ t('立即执行') }}
            </BkRadio>
            <BkRadio label="timer">
              {{ t('定时执行') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          v-if="formData.trigger_checksum_type === 'timer'"
          :label="t('定时执行')"
          property="trigger_checksum_time"
          required>
          <BkDatePicker
            v-model="formData.trigger_checksum_time"
            style="width: 360px"
            type="datetime" />
        </BkFormItem>
      </template>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import dayjs from 'dayjs';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { Affinity, TicketTypes } from '@common/const';

  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import CapacityColumn from './components/capacity-column/Index.vue';
  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    cluster: Pick<
      TendbClusterModel,
      | 'id'
      | 'master_domain'
      | 'bk_cloud_id'
      | 'cluster_capacity'
      | 'cluster_shard_num'
      | 'cluster_spec'
      | 'db_module_id'
      | 'machine_pair_cnt'
      | 'remote_shard_num'
      | 'disaster_tolerance_level'
    >;
    targetCapacity: {
      cluster_capacity: number;
      machine_pair: number;
      spec_id: number;
      spec_name: string;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      bk_cloud_id: 0,
      cluster_capacity: 0,
      cluster_shard_num: 0,
      cluster_spec: {} as TendbClusterModel['cluster_spec'],
      db_module_id: 0,
      disaster_tolerance_level: Affinity.CROS_SUBZONE,
      id: 0,
      machine_pair_cnt: 0,
      master_domain: '',
      remote_shard_num: 0,
    },
    targetCapacity: data.targetCapacity || {
      cluster_capacity: 0,
      machine_pair: 0,
      spec_id: 0,
      spec_name: '',
    },
  });

  const defaultData = () => ({
    backup_source: BackupSourceType.REMOTE,
    need_checksum: false,
    payload: createTickePayload(),
    tableData: [createTableRow()],
    trigger_checksum_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    trigger_checksum_type: 'timer',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  useTicketDetail<TendbCluster.NodeRebalance>(TicketTypes.TENDBCLUSTER_NODE_REBALANCE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        backup_source: details.backup_source,
        need_checksum: details.need_checksum,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterInfo = clusters[item.cluster_id];
          return createTableRow({
            cluster: {
              bk_cloud_id: clusterInfo.bk_cloud_id,
              cluster_capacity: 0,
              cluster_shard_num: item.cluster_shard_num,
              cluster_spec: {} as TendbClusterModel['cluster_spec'],
              db_module_id: clusterInfo.db_module_id,
              disaster_tolerance_level: Affinity.CROS_SUBZONE,
              id: clusterInfo.id,
              machine_pair_cnt: item.prev_machine_pair,
              master_domain: clusterInfo.immute_domain,
              remote_shard_num: item.remote_shard_num,
            },
            targetCapacity: {
              cluster_capacity: item.resource_spec.backend_group.futureCapacity,
              machine_pair: item.resource_spec.backend_group.count,
              spec_id: item.resource_spec.backend_group.spec_id,
              spec_name: item.resource_spec.backend_group.specName,
            },
          });
        }),
        trigger_checksum_time: details.trigger_checksum_time,
        trigger_checksum_type: details.trigger_checksum_type,
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
          spec_id: number;
          specName: string;
        };
      };
      spec_id: number;
    }[];
    need_checksum: boolean;
    trigger_checksum_time: string;
    trigger_checksum_type: string;
  }>(TicketTypes.TENDBCLUSTER_NODE_REBALANCE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    console.log({
      details: {
        backup_source: formData.backup_source,
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
              spec_id: item.targetCapacity.spec_id,
              specName: item.targetCapacity.spec_name,
            },
          },
          spec_id: item.cluster.cluster_spec.spec_id,
        })),
        need_checksum: formData.need_checksum,
        trigger_checksum_time: formData.trigger_checksum_time,
        trigger_checksum_type: formData.trigger_checksum_type,
      },
      remark: formData.payload.remark,
    });

    createTicketRun({
      details: {
        backup_source: formData.backup_source,
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
              spec_id: item.targetCapacity.spec_id,
              specName: item.targetCapacity.spec_name,
            },
          },
          spec_id: item.cluster.cluster_spec.spec_id,
        })),
        need_checksum: formData.need_checksum,
        trigger_checksum_time: formData.trigger_checksum_time,
        trigger_checksum_type: formData.trigger_checksum_type,
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
              bk_cloud_id: item.bk_cloud_id,
              cluster_capacity: item.cluster_capacity,
              cluster_shard_num: item.cluster_shard_num,
              cluster_spec: item.cluster_spec,
              db_module_id: item.db_module_id,
              disaster_tolerance_level: item.disaster_tolerance_level,
              id: item.id,
              machine_pair_cnt: item.machine_pair_cnt,
              master_domain: item.master_domain,
              remote_shard_num: item.remote_shard_num,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };
</script>
