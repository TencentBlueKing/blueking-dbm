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
      :title="t('集群容量变更：通过部署新集群来实现原集群的扩容或缩容（集群分片数不变），可以指定新的版本')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
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
          <EditableColumn
            field="cluster.cluster_type_name"
            :label="t('架构版本')"
            :min-width="150">
            <EditableBlock
              v-model="item.cluster.cluster_type_name"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <RedisVersionColumn
            v-model="item.db_version"
            :cluster="item.cluster" />
          <CurrentCapacityColumn :cluster="item.cluster" />
          <TargetCapacityColumn
            v-model="item.backend_group"
            :row-data="item" />
          <EditableColumn
            field="online_switch_type"
            :label="t('切换模式')"
            :min-width="150">
            <EditableSelect
              v-model="item.online_switch_type"
              :disabled="!item.cluster.id"
              :input-search="false"
              :list="switchModeOptions" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { Affinity, ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import CurrentCapacityColumn from './components/CurrentCapacityColumn.vue';
  import RedisVersionColumn from './components/RedisVersionColumn.vue';
  import TargetCapacityColumn from './components/target-capacity-column/Index.vue';

  interface RowData {
    backend_group: {
      affinity: string;
      capacity: number;
      count: number;
      future_capacity: number;
      group_num: number;
      old_machine_info: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      }[];
      shard_num: number;
      spec_id: number;
      update_mode: string;
    };
    cluster: RedisModel;
    db_version: string;
    online_switch_type: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    backend_group: data.backend_group || {
      affinity: Affinity.CROS_SUBZONE,
      capacity: 1,
      count: 0,
      future_capacity: 1,
      group_num: 0,
      old_machine_info: [],
      shard_num: 0,
      spec_id: 0,
      update_mode: '',
    },
    cluster:
      data.cluster ||
      ({
        bk_cloud_id: 0,
        cluster_capacity: 0,
        cluster_shard_num: 0,
        cluster_spec: {} as RedisModel['cluster_spec'],
        cluster_stats: {} as RedisModel['cluster_stats'],
        cluster_type: ClusterTypes.REDIS_CLUSTER,
        cluster_type_name: '',
        disaster_tolerance_level: Affinity.CROS_SUBZONE,
        id: 0,
        machine_pair_cnt: 0,
        major_version: '',
        master_domain: '',
      } as RedisModel),
    db_version: data.db_version || '',
    online_switch_type: data.online_switch_type || '',
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const switchModeOptions = [
    {
      label: t('需人工确认'),
      value: 'user_confirm',
    },
    {
      label: t('无需确认'),
      value: 'no_confirm',
    },
  ];

  useTicketDetail<Redis.ScaleUpdown>(TicketTypes.REDIS_SCALE_UPDOWN, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterInfo = clusters[item.cluster_id];
          return createTableRow({
            cluster: {
              id: 0,
              master_domain: clusterInfo.immute_domain,
            } as RedisModel,
            db_version: item.db_version,
            online_switch_type: item.online_switch_type,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      bk_cloud_id: number;
      capacity: number;
      cluster_id: number;
      db_version: string;
      display_info: {
        cluster_spec?: RedisModel['cluster_spec'];
        cluster_stats?: RedisModel['cluster_stats'];
      } & Pick<RedisModel, 'cluster_shard_num' | 'cluster_capacity' | 'machine_pair_cnt'>;
      future_capacity: number;
      group_num: number;
      old_nodes: {
        backend_hosts: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      online_switch_type: string;
      resource_spec: {
        backend_group: {
          affinity: Affinity;
          count: number; // 机器组数
          spec_id: number;
        };
      };
      shard_num: number;
      update_mode: string;
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_SCALE_UPDOWN);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          bk_cloud_id: item.cluster.bk_cloud_id,
          capacity: item.backend_group.capacity,
          cluster_id: item.cluster.id,
          db_version: item.db_version,
          display_info: {
            cluster_capacity: item.cluster.cluster_capacity,
            cluster_shard_num: item.cluster.cluster_shard_num,
            cluster_spec: item.cluster.cluster_spec,
            cluster_stats: item.cluster.cluster_stats,
            machine_pair_cnt: item.cluster.machine_pair_cnt,
          },
          future_capacity: item.backend_group.future_capacity,
          group_num: item.backend_group.group_num,
          old_nodes: {
            backend_hosts: item.backend_group.old_machine_info,
          },
          online_switch_type: item.online_switch_type,
          resource_spec: {
            backend_group: {
              affinity: item.backend_group.affinity as Affinity,
              count: item.backend_group.count,
              spec_id: item.backend_group.spec_id,
            },
          },
          shard_num: item.backend_group.shard_num,
          update_mode: item.backend_group.update_mode,
        })),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: RedisModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: item,
            db_version: item.major_version,
            online_switch_type: 'user_confirm',
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
