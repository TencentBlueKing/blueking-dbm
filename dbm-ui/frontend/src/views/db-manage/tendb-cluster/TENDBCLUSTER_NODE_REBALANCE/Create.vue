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
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <Column
            field="cluster.cluster_spec.spec_name"
            :label="t('当前资源规格')"
            :min-width="150">
            <Block
              v-model="item.cluster.cluster_spec.spec_name"
              :placeholder="t('自动生成')" />
          </Column>
          <Column
            field="cluster.cluster_shard_num"
            :label="t('集群分片数')"
            :min-width="150">
            <Block>
              <span v-if="item.cluster.cluster_shard_num">{{ item.cluster.cluster_shard_num }}</span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('自动生成') }}
              </span>
            </Block>
          </Column>
          <Column
            field="cluster.machine_pair_cnt"
            :label="t('部署机器组数')"
            :min-width="150">
            <Block>
              <span v-if="item.cluster.machine_pair_cnt">{{ item.cluster.machine_pair_cnt }}</span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('自动生成') }}
              </span>
            </Block>
          </Column>
          <Column
            field="cluster.cluster_capacity"
            :label="t('当前总容量')"
            :min-width="150">
            <Block>
              <span v-if="item.cluster.cluster_capacity">{{ item.cluster.cluster_capacity }} G</span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('自动生成') }}
              </span>
            </Block>
          </Column>
          <TargetCapcityColumn
            v-model="item.targetCapacity"
            :cluster="item.cluster" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
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
  import dayjs from 'dayjs';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';
  import TargetCapcityColumn from './components/TargetCapcityColumn.vue';

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
      spec_id: number;
      spec_name: string;
      machine_pair: number;
      cluster_capacity: number;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
      bk_cloud_id: 0,
      cluster_capacity: 0,
      cluster_shard_num: 0,
      cluster_spec: {} as TendbClusterModel['cluster_spec'],
      db_module_id: 0,
      machine_pair_cnt: 0,
      remote_shard_num: 0,
      disaster_tolerance_level: 'CROS_SUBZONE',
    },
    targetCapacity: data.targetCapacity || {
      spec_id: 0,
      spec_name: '',
      machine_pair: 0,
      cluster_capacity: 0,
    },
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    backup_source: BackupSourceType.REMOTE,
    need_checksum: false,
    trigger_checksum_type: 'timer',
    trigger_checksum_time: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_id: number;
      bk_cloud_id: number;
      db_module_id: number;
      cluster_shard_num: number;
      prev_machine_pair: number;
      prev_cluster_spec_name: string;
      remote_shard_num: number;
      resource_spec: {
        backend_group: {
          affinity: string;
          count: number;
          futureCapacity: number;
          specName: string;
          spec_id: number;
        };
      };
    }[];
    need_checksum: boolean;
    trigger_checksum_time: string;
    trigger_checksum_type: string;
    remark: string;
  }>(TicketTypes.TENDBCLUSTER_NODE_REBALANCE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        backup_source: formData.backup_source,
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          bk_cloud_id: item.cluster.bk_cloud_id,
          db_module_id: item.cluster.db_module_id,
          cluster_shard_num: item.cluster.cluster_shard_num,
          prev_machine_pair: item.cluster.machine_pair_cnt,
          prev_cluster_spec_name: item.cluster.cluster_spec.spec_name,
          remote_shard_num: Math.ceil(item.cluster.cluster_shard_num / item.targetCapacity.machine_pair),
          resource_spec: {
            backend_group: {
              affinity: item.cluster.disaster_tolerance_level,
              count: item.targetCapacity.machine_pair,
              futureCapacity: item.targetCapacity.cluster_capacity,
              specName: item.targetCapacity.spec_name,
              spec_id: item.targetCapacity.spec_id,
            },
          },
        })),
        need_checksum: formData.need_checksum,
        trigger_checksum_time: formData.trigger_checksum_time,
        trigger_checksum_type: formData.trigger_checksum_type,
        remark: formData.remark,
      },
      remark: formData.remark,
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
              id: item.id,
              master_domain: item.master_domain,
              bk_cloud_id: item.bk_cloud_id,
              cluster_capacity: item.cluster_capacity,
              cluster_shard_num: item.cluster_shard_num,
              cluster_spec: item.cluster_spec,
              db_module_id: item.db_module_id,
              machine_pair_cnt: item.machine_pair_cnt,
              remote_shard_num: item.remote_shard_num,
              disaster_tolerance_level: item.disaster_tolerance_level,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
