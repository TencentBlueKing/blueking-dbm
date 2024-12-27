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
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumnGroup
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit"
            @change="(data) => handleInputed(data, item)" />
          <RedisVersionColumn
            v-model="item.version"
            :cluster-id="item.cluster.id" />
          <CurrentCapacityColumn :cluster="item.cluster" />
          <TargetCapacityColumn
            v-model="item.backendGroup"
            :cluster="item.cluster"
            :current-capacity="item.currentCapacity"
            :version="item.version" />
          <SwitchModeColumn
            v-model="item.switchMode"
            :disabled="!item.cluster.id" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <TicketRemark v-model="formData.remark" />
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

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/ticket-remark/Index.vue';
  import { AffinityType } from '@views/db-manage/redis/common/types';

  import ClusterColumnGroup from './components/ClusterColumnGroup.vue';
  import CurrentCapacityColumn from './components/CurrentCapacityColumn.vue';
  import RedisVersionColumn from './components/RedisVersionColumn.vue';
  import SwitchModeColumn from './components/SwitchModeColumn.vue';
  import TargetCapacityColumn from './components/TargetCapacityColumn.vue';

  interface RowData {
    cluster: Pick<RedisModel, 'id' | 'master_domain' | 'cluster_type' | 'cluster_type_name' | 'bk_cloud_id'> & {
      cluster_stats?: RedisModel['cluster_stats'];
      cluster_spec?: RedisModel['cluster_spec'];
      group_num: RedisModel['machine_pair_cnt'];
      shard_num: RedisModel['cluster_shard_num'];
    };
    version: string;
    currentCapacity: {
      used: number;
      total: number;
    };
    backendGroup: {
      spec_id: number;
      count: number;
      affinity: string;
      group_num: number;
      shard_num: number;
    };
    switchMode: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
      cluster_type: '',
      cluster_type_name: '',
      shard_num: 0,
      group_num: 0,
      bk_cloud_id: 0,
    },
    version: data.version || '',
    currentCapacity: data.currentCapacity || {
      used: 0,
      total: 1,
    },
    backendGroup: data.backendGroup || {
      spec_id: 0,
      count: 0,
      affinity: AffinityType.CROS_SUBZONE,
      shard_num: 0,
      group_num: 0,
    },
    switchMode: data.switchMode || '',
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => selected.value.filter((item) => item.master_domain === value).length < 2,
        message: t('目标集群重复'),
        trigger: 'change',
      },
    ],
  };

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    ip_source: 'resource_pool';
    infos: {
      cluster_id: number;
      bk_cloud_id: number;
      db_version: string;
      shard_num: number;
      group_num: number;
      online_switch_type: string;
      resource_spec: {
        backend_group: {
          spec_id: number;
          count: number; // 机器组数
          affinity: AffinityType;
        };
      };
      old_nodes?: {
        backend_hosts: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      display_info: Pick<RedisModel, 'cluster_shard_num' | 'cluster_capacity' | 'machine_pair_cnt'> & {
        cluster_stats?: RedisModel['cluster_stats'];
        cluster_spec?: RedisModel['cluster_spec'];
      };
    }[];
  }>(TicketTypes.REDIS_SCALE_UPDOWN);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun(
      {
        ip_source: 'resource_pool',
        infos: formData.tableData.map((item) => ({
          bk_cloud_id: item.cluster.bk_cloud_id,
          cluster_id: item.cluster.id,
          db_version: item.version,
          shard_num: item.backendGroup.shard_num,
          group_num: item.backendGroup.group_num,
          resource_spec: {
            backend_group: {
              spec_id: item.backendGroup.spec_id,
              count: item.backendGroup.count,
              affinity: item.backendGroup.affinity as AffinityType,
            },
          },
          online_switch_type: item.switchMode,
          display_info: {
            cluster_capacity: item.currentCapacity.total,
            cluster_shard_num: item.cluster.shard_num,
            cluster_spec: item.cluster?.cluster_spec,
            cluster_stats: item.cluster?.cluster_stats,
            machine_pair_cnt: item.cluster.group_num,
          },
        })),
      },
      formData.remark,
    );
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  /**
   * redis model转换成表格行数据
   */
  const generateTableRow = (item: RedisModel) =>
    createTableRow({
      cluster: {
        id: item.id,
        master_domain: item.master_domain,
        cluster_type: item.cluster_type,
        cluster_type_name: item.cluster_type_name,
        cluster_stats: item.cluster_stats,
        cluster_spec: item.cluster_spec,
        group_num: item.machine_pair_cnt,
        shard_num: item.cluster_shard_num,
        bk_cloud_id: item.bk_cloud_id,
      },
      version: item.major_version,
      currentCapacity: {
        used: 1,
        total: item.cluster_capacity,
      },
      backendGroup: {
        spec_id: 0,
        count: 0,
        affinity: item.disaster_tolerance_level,
        shard_num: 0,
        group_num: 0,
      },
    });

  const handleBatchEdit = (list: RedisModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(generateTableRow(item));
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleInputed = (item: RedisModel, row: RowData) => {
    Object.assign(row, generateTableRow(item));
  };
</script>
