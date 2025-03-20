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
  <EditableColumn
    :disabled-method="disabledMethod"
    field="backend_group.spec_id"
    :label="t('目标容量')"
    :min-width="150"
    required
    :rule="rules">
    <div class="capacity-box">
      <EditableInput
        v-if="!modelValue.spec_id || !activeRowData || !targetObj"
        :placeholder="t('请选择')"
        @focus="handleShowSideslider">
        <template #append>
          <DbIcon
            class="down-icon"
            type="down-big" />
        </template>
      </EditableInput>
      <div
        v-else
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('目标容量') }}：</div>
          <div class="item-content">
            <ClusterCapacityUsageRate :cluster-stats="targetClusterStats" />
            <ValueDiff
              :current-value="currentCapacity"
              num-unit="G"
              :target-value="targetObj.capacity" />
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('资源规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="targetObj.spec"
              :hide-qps="!targetObj.spec.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('机器组数') }}：</div>
          <div class="item-content">
            {{ targetObj.groupNum }}
            <ValueDiff
              :current-value="activeRowData.groupNum"
              :show-rate="false"
              :target-value="targetObj.groupNum" />
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('机器数量') }}：</div>
          <div class="item-content">
            {{ targetObj.groupNum * 2 }}
            <ValueDiff
              :current-value="activeRowData.groupNum * 2"
              :show-rate="false"
              :target-value="targetObj.groupNum * 2" />
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('分片数') }}：</div>
          <div class="item-content">
            {{ targetObj.shardNum }}
            <ValueDiff
              :current-value="activeRowData.shardNum"
              :show-rate="false"
              :target-value="targetObj.shardNum" />
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('变更方式') }}：</div>
          <div class="item-content">
            {{ targetObj.updateMode === 'keep_current_machines' ? t('原地变更') : t('替换变更') }}
          </div>
        </div>
      </div>
    </div>
  </EditableColumn>
  <ClusterTargetPlan
    v-if="rowData.cluster?.cluster_stats"
    :cluster-id="rowData.cluster.id"
    :cluster-stats="rowData.cluster.cluster_stats"
    :data="activeRowData"
    hide-shard-column
    :is-show="showClusterTargetPlan"
    :target-object="targetObj"
    :target-verison="rowData.db_version"
    :title="t('选择集群容量变更部署方案')"
    @click-cancel="() => (showClusterTargetPlan = false)"
    @click-confirm="handleChoosedTargetCapacity"
    @target-stats-change="handleTargetStatsChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { ClusterTypes } from '@common/const';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  import { convertStorageUnits } from '@utils';

  import ClusterTargetPlan, {
    type Props as TargetPlanProps,
    type SpecResultInfo,
    type TargetInfo,
  } from './ClusterDeployPlan.vue';

  interface Props {
    rowData: {
      cluster: {
        group_num: RedisModel['machine_pair_cnt'];
        shard_num: RedisModel['cluster_shard_num'];
      } & Pick<
        RedisModel,
        'id' | 'master_domain' | 'cluster_type' | 'cluster_type_name' | 'bk_cloud_id' | 'cluster_spec' | 'cluster_stats'
      >;
      cluster_capacity: {
        total: number;
        used: number;
      };
      db_version: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
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
  }>({
    default: () => ({}),
  });

  const { t } = useI18n();

  const showClusterTargetPlan = ref(false);
  const activeRowData = ref<TargetPlanProps['data']>();
  const futureCapacity = ref(1);
  const targetObj = ref<TargetInfo>();
  const targetClusterStats = ref<RedisModel['cluster_stats']>();
  const currentCapacity = computed(() => {
    if (_.isEmpty(props.rowData.cluster?.cluster_stats)) {
      return props.rowData.cluster_capacity?.total ?? 0;
    }
    return convertStorageUnits(props.rowData.cluster.cluster_stats.total, 'B', 'GB');
  });

  const rules = [
    {
      message: t('请选择目标容量'),
      validator: (value: string) => Boolean(value),
    },
  ];

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'backend_group.spec_id' && !rowData.db_version) {
      return t('请先选择版本');
    }
    return '';
  };

  const handleShowSideslider = () => {
    const {
      bk_cloud_id: bkCloudId,
      cluster_spec: spec,
      cluster_type: clusterType,
      master_domain: domain,
      shard_num: shardNum,
    } = props.rowData.cluster;
    if (spec) {
      activeRowData.value = {
        bkCloudId,
        capacity: props.rowData.cluster_capacity,
        cloudId: bkCloudId,
        clusterType: clusterType ?? ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        currentSepc: {
          cpu: spec.cpu,
          id: spec.spec_id,
          mem: spec.mem,
          name: spec.spec_name || '',
          qps: spec.qps,
          storage_spec: spec.storage_spec,
        },
        groupNum: props.rowData.cluster.group_num,
        shardNum,
        targetCluster: domain,
      };
      showClusterTargetPlan.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (specResultInfo: SpecResultInfo, capacity: number, targetInfo: TargetInfo) => {
    futureCapacity.value = capacity;
    targetObj.value = targetInfo;
    modelValue.value = {
      affinity: modelValue.value.affinity,
      capacity: capacity || 1,
      count: targetObj.value.requireMachineGroupNum,
      future_capacity: capacity || 1,
      group_num: specResultInfo.machine_pair,
      old_machine_info: targetInfo.oldMachineInfo,
      shard_num: specResultInfo.cluster_shard_num,
      spec_id: specResultInfo.spec_id,
      update_mode: targetObj.value.updateMode,
    };
    showClusterTargetPlan.value = false;
  };

  const handleTargetStatsChange = (value: RedisModel['cluster_stats']) => {
    targetClusterStats.value = value;
  };
</script>

<style lang="less" scoped>
  .down-icon {
    font-size: 15px;
    color: #979ba5;
  }

  .capacity-box {
    flex: 1;
    width: 100%;

    .display-content {
      padding: 11px 16px;
      overflow: hidden;
      line-height: 20px;
      white-space: nowrap;

      .item {
        display: flex;
        width: 100%;

        .item-title {
          width: 64px;
          text-align: right;
        }

        .item-content {
          flex: 1;
          display: flex;
          align-items: center;

          .percent {
            margin-left: 4px;
            font-size: 12px;
            font-weight: bold;
            color: #313238;
          }

          .spec {
            margin-left: 2px;
            font-size: 12px;
            color: #979ba5;
          }

          :deep(.render-spec-box) {
            height: 22px;
            padding: 0;
          }
        }
      }
    }
  }
</style>
