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
    <div class="cluster-shard-update">
      <BkAlert
        closable
        theme="info"
        :title="t('集群分片变更：通过部署新集群来实现增加或减少原集群的分片数，可以指定新的版本')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
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
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <TargetVersionSelectColumn
              v-model="item.db_version"
              :cluster-type="item.cluster.cluster_type"
              :current-versions="item.cluster.major_version ? [item.cluster.major_version] : []"
              :label="t('Redis 版本')" />
            <CurrentCapacityColumn :cluster="item.cluster" />
            <TargetCapacityColumn
              v-model="item.target_capacity"
              :cluster="item.cluster"
              :target-cluster-type="item.cluster.cluster_type"
              :title="t('选择集群分片变更部署方案')" />
            <EditableColumn
              :label="t('切换模式')"
              :width="150">
              <template #head>
                <BkPopover
                  :content="t('后端存储实例与 Proxy 的关系切换')"
                  placement="top"
                  theme="dark">
                  <span style="border-bottom: 1px dashed #979ba5">{{ t('切换模式') }}</span>
                </BkPopover>
              </template>
              <EditableBlock>
                {{ t('需人工确认') }}
              </EditableBlock>
            </EditableColumn>
            <!-- <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" /> -->
          </EditableRow>
        </EditableTable>
        <BkFormItem
          :label="t('校验与修复类型')"
          property="data_check_repair_setting_type"
          required>
          <BkRadioGroup v-model="formData.data_check_repair_setting_type">
            <BkRadio :label="RepairAndVerifyModes.DATA_CHECK_AND_REPAIR">
              <BkPopover
                placement="top"
                theme="dark">
                <span>{{ t(repairAndVerifyTypeList[0].label) }}</span>
                <template #content>
                  <div>{{ t('校验：将会对集群进行大量的读操作，可能会影响性能。') }}</div>
                  <div>{{ t('修复：修复将会覆盖同名 Key 对应的数据（覆盖更新，非追加）') }}</div>
                </template>
              </BkPopover>
            </BkRadio>
            <BkRadio :label="RepairAndVerifyModes.DATA_CHECK_ONLY">
              <BkPopover
                :content="t('校验将会对集群进行大量的读操作，可能会影响性能')"
                placement="top"
                theme="dark">
                <span>{{ t(repairAndVerifyTypeList[1].label) }}</span>
              </BkPopover>
            </BkRadio>
            <BkRadio :label="RepairAndVerifyModes.NO_CHECK_NO_REPAIR">
              {{ t(repairAndVerifyTypeList[2].label) }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          v-if="formData.data_check_repair_setting_type !== RepairAndVerifyModes.NO_CHECK_NO_REPAIR"
          :label="t('校验与修复频率设置')"
          property="data_check_repair_setting_execution_frequency"
          required>
          <BkSelect
            v-model="formData.data_check_repair_setting_execution_frequency"
            style="width: 460px">
            <BkOption
              v-for="(item, index) in repairAndVerifyFrequencyList"
              :key="index"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
        </BkFormItem>
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
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { RepairAndVerifyFrequencyModes, RepairAndVerifyModes } from '@services/model/redis/redis-dst-history-job';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { Affinity, ClusterTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/db-manage/redis/common/const';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import TargetVersionSelectColumn from '@views/db-manage/redis/common/toolbox-field/target-version-select-column/Index.vue';

  import CurrentCapacityColumn from './components/CurrentCapacityColumn.vue';
  import TargetCapacityColumn from './components/target-capacity-column/Index.vue';

  interface IDataRow {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      city_code: string;
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_stats: RedisModel['cluster_stats'];
      cluster_type: string;
      cluster_type_name: string;
      disaster_tolerance_level: string;
      id: number;
      machine_pair_cnt: number;
      major_version: string;
      master_domain: string;
      proxy: RedisModel['proxy'];
    };
    db_version: string;
    target_capacity: {
      backend_group: {
        count: string | number;
        id: number;
      };
      capacity: number;
      cluster_shard_num: number;
      future_capacity: number;
      proxy: {
        count: number;
        id: number;
      };
    };
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        city_code: '',
        cluster_capacity: 0,
        cluster_shard_num: 0,
        cluster_spec: {} as RedisModel['cluster_spec'],
        cluster_stats: {} as RedisModel['cluster_stats'],
        cluster_type: '',
        cluster_type_name: '',
        disaster_tolerance_level: '',
        id: 0,
        machine_pair_cnt: 0,
        major_version: '',
        master_domain: '',
        proxy: [] as RedisModel['proxy'],
      },
      values.cluster,
    ),
    db_version: values?.db_version || '',
    target_capacity: Object.assign(
      {
        backend_group: {
          count: '' as string | number,
          id: 0,
        },
        capacity: 0,
        cluster_shard_num: 0,
        future_capacity: 0,
        proxy: {
          count: 0,
          id: 0,
        },
      },
      values.target_capacity,
    ),
  });

  const createDefaultFormData = () => ({
    data_check_repair_setting_execution_frequency: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
    data_check_repair_setting_type: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Redis.ClusterShardNumUpdate>(TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        data_check_repair_setting_execution_frequency: details.data_check_repair_setting.execution_frequency,
        data_check_repair_setting_type: details.data_check_repair_setting.type,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.src_cluster].immute_domain,
            } as IDataRow['cluster'],
            db_version: infoItem.db_version,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    data_check_repair_setting: {
      execution_frequency: string;
      type: string;
    };
    infos: {
      capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec']; // 展示字段
      cluster_stats: RedisModel['cluster_stats']; // 展示字段
      current_shard_num: number;
      current_spec_id: number;
      db_version: string;
      future_capacity: number;
      machine_pair_cnt: number; // 展示字段
      online_switch_type: 'user_confirm';
      proxy: RedisModel['proxy']; // 展示字段
      resource_spec: {
        backend_group: {
          affinity: string;
          count: number; // 机器组数
          spec_id: number;
        };
        proxy: {
          affinity: string;
          count: number;
          spec_id: number;
        };
      };
      src_cluster: number;
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE);

  const editableTableRef = useTemplateRef('editableTable');

  const formData = reactive(createDefaultFormData());

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
      multiple: false,
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  // const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      // if (!selectedMap.value[item.master_domain]) {
      newList.push(
        createRowData({
          cluster: {
            bk_biz_id: item.bk_biz_id,
            bk_cloud_id: item.bk_cloud_id,
            city_code: item.city,
            cluster_capacity: item.cluster_capacity,
            cluster_shard_num: item.cluster_shard_num,
            cluster_spec: item.cluster_spec,
            cluster_stats: item.cluster_stats,
            cluster_type: item.cluster_type,
            cluster_type_name: item.cluster_type_name,
            disaster_tolerance_level: item.disaster_tolerance_level,
            id: item.id,
            machine_pair_cnt: item.machine_pair_cnt,
            major_version: item.major_version,
            master_domain: item.master_domain,
            proxy: item.proxy,
          },
        }),
      );
      // }
    });

    // formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    formData.tableData = newList;
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          data_check_repair_setting: {
            execution_frequency: formData.data_check_repair_setting_execution_frequency,
            type: formData.data_check_repair_setting_type,
          },
          infos: formData.tableData.map((tableItem) => ({
            capacity: tableItem.target_capacity.capacity,
            cluster_shard_num: tableItem.target_capacity.cluster_shard_num,
            cluster_spec: tableItem.cluster.cluster_spec,
            cluster_stats: tableItem.cluster.cluster_stats,
            current_shard_num: tableItem.cluster.cluster_shard_num,
            current_spec_id: tableItem.cluster.cluster_spec.spec_id,
            db_version: tableItem.db_version,
            future_capacity: tableItem.target_capacity.future_capacity,
            machine_pair_cnt: tableItem.cluster.machine_pair_cnt,
            online_switch_type: 'user_confirm',
            proxy: tableItem.cluster.proxy,
            resource_spec: {
              backend_group: {
                affinity: tableItem.cluster.disaster_tolerance_level || Affinity.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
                count: Number(tableItem.target_capacity.backend_group.count), // 机器组数
                spec_id: tableItem.target_capacity.backend_group.id,
              },
              proxy: {
                affinity: tableItem.cluster.disaster_tolerance_level || Affinity.CROS_SUBZONE,
                count: tableItem.target_capacity.proxy.count, // 机器组数
                spec_id: tableItem.target_capacity.proxy.id,
              },
            },
            src_cluster: tableItem.cluster.id,
          })),
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
  .cluster-shard-update {
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
