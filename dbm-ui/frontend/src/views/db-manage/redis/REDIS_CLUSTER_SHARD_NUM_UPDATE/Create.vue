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
          class="mt16 mb16"
          :model="formData.tableData"
          :rules="rules">
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
            <EditableColumn
              :label="t('当前集群容量/QPS')"
              :width="200">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{
                  item.cluster.id
                    ? `${item.cluster.cluster_capacity}G_${item.cluster.cluster_spec?.qps.max}/s（${item.cluster.cluster_shard_num} 分片)`
                    : ''
                }}
              </EditableBlock>
            </EditableColumn>
            <TargetCapacityColumn
              v-model="item.target_capacity"
              :cluster="item.cluster"
              :title="t('选择集群分片变更部署方案')" />
            <TargetVersionSelectColumn
              v-model="item.db_version"
              :cluster-type="item.cluster.cluster_type"
              :current-versions="item.cluster.major_version ? [item.cluster.major_version] : []"
              :table-data="formData.tableData.map((tableItem) => tableItem.cluster)"
              @batch-edit="handleVersionBatchEdit" />
            <EditableColumn
              :label="t('切换模式')"
              :width="200">
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
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
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
        <TicketPayload v-model="formData" />
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
  import { RepairAndVerifyFrequencyModes, RepairAndVerifyModes } from '@services/model/redis/redis-dst-history-job';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/db-manage/redis/common/const';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import TargetCapacityColumn from '@views/db-manage/redis/common/toolbox-field/target-capacity-column/Index.vue';
  import TargetVersionSelectColumn from '@views/db-manage/redis/common/toolbox-field/target-version-select-column/Index.vue';
  import { AffinityType } from '@views/db-manage/redis/common/types';

  interface IDataRow {
    cluster: {
      id: number;
      master_domain: string;
      cluster_type: string;
      cluster_type_name: string;
      bk_cloud_id: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_capacity: number;
      cluster_shard_num: number;
      machine_pair_cnt: number;
      major_version: string;
      disaster_tolerance_level: string;
      proxy: RedisModel['proxy'];
    };
    target_capacity: {
      cluster_shard_num: number;
      capacity: number;
      future_capacity: number;
      spec_id: number;
      count: number;
    };
    db_version: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
        cluster_type: '',
        cluster_type_name: '',
        bk_cloud_id: 0,
        cluster_spec: {} as RedisModel['cluster_spec'],
        cluster_capacity: 0,
        cluster_shard_num: 0,
        machine_pair_cnt: 0,
        major_version: '',
        disaster_tolerance_level: '',
        proxy: [] as RedisModel['proxy'],
      },
      values.cluster,
    ),
    target_capacity: Object.assign(
      {
        cluster_shard_num: 0,
        capacity: 0,
        future_capacity: 0,
        spec_id: 0,
        count: 0,
      },
      values.target_capacity,
    ),
    db_version: values?.db_version || '',
  });

  const createDefaultFormData = () => ({
    tableData: [createRowData()],
    data_check_repair_setting_type: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
    data_check_repair_setting_execution_frequency: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
    ...createTickePayload(),
  });

  const { t } = useI18n();

  useTicketDetail<Redis.ClusterShardNumUpdate>(TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;
      Object.assign(formData, {
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.src_cluster].immute_domain,
            } as IDataRow['cluster'],
            db_version: infoItem.db_version,
          }),
        ),
        data_check_repair_setting_type: details.data_check_repair_setting.type,
        data_check_repair_setting_execution_frequency: details.data_check_repair_setting.execution_frequency,
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    data_check_repair_setting: {
      type: string;
      execution_frequency: string;
    };
    ip_source: 'resource_pool';
    infos: {
      src_cluster: number;
      current_shard_num: number;
      current_spec_id: number;
      cluster_shard_num: number;
      db_version: string;
      online_switch_type: 'user_confirm';
      capacity: number;
      future_capacity: number;
      resource_spec: {
        proxy: {
          spec_id: number;
          count: number;
          affinity: string;
        };
        backend_group: {
          spec_id: number;
          count: number; // 机器组数
          affinity: string;
        };
      };
    }[];
  }>(TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE);

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = formData.tableData.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
  };

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
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterColumn>['selected'] = {
      [ClusterTypes.REDIS]: [],
    };
    formData.tableData.forEach((tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id && masterDomain) {
        selectedClusters[ClusterTypes.REDIS].push({
          id,
          master_domain: masterDomain,
        });
      }
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        const domain = item.master_domain;
        if (!clusterMemo.value[domain]) {
          newList.push(
            createRowData({
              cluster: {
                id: item.id,
                master_domain: item.master_domain,
                cluster_type: item.cluster_type,
                cluster_type_name: item.cluster_type_name,
                bk_cloud_id: item.bk_cloud_id,
                cluster_spec: item.cluster_spec,
                cluster_capacity: item.cluster_capacity,
                cluster_shard_num: item.cluster_shard_num,
                machine_pair_cnt: item.machine_pair_cnt,
                major_version: item.major_version,
                disaster_tolerance_level: item.disaster_tolerance_level,
                proxy: item.proxy,
              },
            }),
          );
        }
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleVersionBatchEdit = (value: string) => {
    formData.tableData.forEach((tableItem) => {
      Object.assign(tableItem, {
        db_version: value,
      });
    });
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          data_check_repair_setting: {
            type: formData.data_check_repair_setting_type,
            execution_frequency: formData.data_check_repair_setting_execution_frequency,
          },
          ip_source: 'resource_pool',
          infos: formData.tableData.map((tableItem) => ({
            src_cluster: tableItem.cluster.id,
            current_shard_num: tableItem.cluster.cluster_shard_num,
            cluster_shard_num: tableItem.target_capacity.cluster_shard_num,
            current_spec_id: tableItem.cluster.cluster_spec.spec_id,
            capacity: tableItem.target_capacity.capacity,
            future_capacity: tableItem.target_capacity.future_capacity,
            resource_spec: {
              proxy: {
                spec_id: tableItem.cluster.proxy[0].spec_config.id,
                count: new Set(tableItem.cluster.proxy.map((item) => item.ip)).size,
                affinity: tableItem.cluster.disaster_tolerance_level || AffinityType.CROS_SUBZONE,
              },
              backend_group: {
                spec_id: tableItem.target_capacity.spec_id,
                count: tableItem.target_capacity.count, // 机器组数
                affinity: tableItem.cluster.disaster_tolerance_level || AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
              },
            },
            db_version: tableItem.db_version,
            online_switch_type: 'user_confirm',
          })),
        },
        remark: formData.remark,
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
