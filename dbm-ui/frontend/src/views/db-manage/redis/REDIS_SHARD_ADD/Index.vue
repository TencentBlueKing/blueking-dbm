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
    <div class="redis-shard-add">
      <BkAlert
        closable
        theme="info"
        :title="t('增加或减少分片（机器）数量，分片数变化后会做Slot搬迁。仅支持RedisCluster 和 Tendisplus')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('集群类型')"
          required>
          <BkRadioGroup
            v-model="formData.ticket_type"
            style="width: 400px"
            type="card"
            @change="handleClusterTypeChange">
            <BkRadioButton :label="TicketTypes.REDIS_SHARD_ADD">
              {{ t('增加分片数') }}
            </BkRadioButton>
            <BkRadioButton :label="TicketTypes.REDIS_SHARD_REDUCE">
              {{ t('减少分片数') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <BatchInput
          :config="batchInputConfig"
          @change="handleBatchInput" />
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
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
              readonly
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <CurrentCapacityColumn :cluster="item.cluster" />
            <GroupNumColumn
              v-model="item.group_num"
              :cluster-id="item.cluster.id"
              @batch-edit="handleBatchEdit" />
            <TargetCapacityColumn
              v-model="item.future_capacity"
              :add-group-num="item.group_num"
              :cluster="item.cluster" />
            <ResourceTagColumn
              v-model="item.labels"
              @batch-edit="handleBatchEdit" />
            <AvailableResourceColumn
              :params="{
                city: item.cluster.region,
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MONGODB, 'PUBLIC'],
                spec_id: item.cluster.cluster_spec.spec_id,
                labels: item.labels.map((item) => item.id).join(','),
              }" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
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
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import CurrentCapacityColumn from './components/CurrentCapacityColumn.vue';
  import GroupNumColumn from './components/GroupNumColumn.vue';
  import TargetCapacityColumn from './components/TargetCapacityColumn.vue';

  interface IDataRow {
    cluster: {
      bk_cloud_id: number;
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_stats: RedisModel['cluster_stats'];
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      machine_pair_cnt: number;
      major_version: string;
      master_domain: string;
      region: string;
    };
    future_capacity: number;
    group_num: number;
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
  }

  const createRowData = (values: DeepPartial<IDataRow> = {}) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_capacity: 0,
        cluster_shard_num: 0,
        cluster_spec: {} as RedisModel['cluster_spec'],
        cluster_stats: {} as RedisModel['cluster_stats'],
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        machine_pair_cnt: 0,
        major_version: '',
        master_domain: '',
        region: '',
      },
      values.cluster,
    ),
    future_capacity: values?.future_capacity || 0,
    group_num: values?.group_num || 1,
    labels: (values.labels || []) as IDataRow['labels'],
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
    ticket_type: TicketTypes.REDIS_SHARD_ADD,
  });

  const { t } = useI18n();
  const router = useRouter();

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
    {
      case: '1',
      key: 'count',
      label: t('增加机器组数'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  useTicketDetail<Redis.ResourcePool.ShardAdd>(TicketTypes.REDIS_SHARD_ADD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            group_num: infoItem.resource_spec.backend_group.count,
            labels: (infoItem.resource_spec.backend_group.labels || []).map((item) => ({
              id: Number(item),
              value: '',
            })),
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Redis.ResourcePool.ShardAdd['infos'];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_SHARD_ADD);

  const editableTableRef = useTemplateRef('editableTable');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            // ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            // ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterTypeChange = () => {
    router.push({
      name: TicketTypes.REDIS_SHARD_REDUCE,
    });
  };

  const handleBatchEdit = (value: string | number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_capacity: item.cluster_capacity,
              cluster_shard_num: item.cluster_shard_num,
              cluster_spec: item.cluster_spec,
              cluster_stats: item.cluster_stats,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              machine_pair_cnt: item.machine_pair_cnt,
              major_version: item.major_version,
              master_domain: item.master_domain,
              region: item.region,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
        group_num: item.count ? Number(item.count) : 1,
        labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => {
            const newGroupNum = tableItem.cluster.machine_pair_cnt + tableItem.group_num;
            const machineShardNum = tableItem.cluster.cluster_shard_num / tableItem.cluster.machine_pair_cnt;

            return {
              bk_cloud_id: tableItem.cluster.bk_cloud_id,
              capacity: tableItem.cluster.cluster_capacity,
              cluster_id: tableItem.cluster.id,
              db_version: tableItem.cluster.major_version,
              future_capacity: tableItem.future_capacity,
              group_num: newGroupNum, // 新机器组数
              resource_spec: {
                backend_group: {
                  count: tableItem.group_num,
                  label_names: tableItem.labels.map((item) => item.value),
                  labels: tableItem.labels.map((item) => String(item.id)),
                  spec_id: tableItem.cluster.cluster_spec.spec_id,
                },
              },
              shard_num: newGroupNum * machineShardNum, // 新集群分片数
              update_mode: 'slot_migrate_up',
            };
          }),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .redis-shard-add {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
