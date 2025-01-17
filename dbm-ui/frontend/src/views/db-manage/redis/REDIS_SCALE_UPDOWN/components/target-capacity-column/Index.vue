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
    field="backendGroup.spec_id"
    :label="t('目标容量')"
    :min-width="150"
    required
    :rule="rules">
    <div class="capacity-box">
      <EditableInput
        v-if="!localValue || !activeRowData || !targetObj"
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
    :target-verison="rowData.version"
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
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    spec_id: number;
    count: number;
    affinity: string;
    group_num: number;
    shard_num: number;
  }>({
    default: () => ({}),
  });

  const { t } = useI18n();

  const localValue = reactive({
    cluster_capacity: 0,
    max: 0,
    cluster_shard_num: 0,
    spec_id: 0,
    machine_pair: 0,
  });
  const showClusterTargetPlan = ref(false);
  const activeRowData = ref<TargetPlanProps['data']>();
  const futureCapacity = ref(1);
  const targetObj = ref<TargetInfo>();
  const targetClusterStats = ref<RedisModel['cluster_stats']>();
  const currentCapacity = computed(() => {
    if (_.isEmpty(props.rowData.cluster?.cluster_stats)) {
      return props.rowData.currentCapacity?.total ?? 0;
    }
    return convertStorageUnits(props.rowData.cluster.cluster_stats.total, 'B', 'GB');
  });

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择目标容量'),
    },
  ];

  watch(
    () => props.rowData.cluster,
    () => {
      localValue.cluster_shard_num = props.rowData.cluster.shard_num;
      localValue.machine_pair = props.rowData.cluster.group_num;
    },
  );

  watch(
    () => [localValue, targetObj.value],
    () => {
      const cloneData = _.cloneDeep(modelValue.value);
      modelValue.value = {
        spec_id: localValue.spec_id,
        count: targetObj.value!.requireMachineGroupNum,
        affinity: cloneData.affinity,
        shard_num: localValue.cluster_shard_num,
        group_num: localValue.machine_pair,
      };
    },
  );

  const handleShowSideslider = () => {
    const {
      master_domain: domain,
      cluster_spec: spec,
      cluster_type: clusterType,
      bk_cloud_id: bkCloudId,
      shard_num: shardNum,
    } = props.rowData.cluster;
    if (spec) {
      activeRowData.value = {
        targetCluster: domain,
        currentSepc: {
          name: spec.spec_name || '',
          cpu: spec.cpu,
          id: spec.spec_id,
          mem: spec.mem,
          qps: spec.qps,
          storage_spec: spec.storage_spec,
        },
        capacity: props.rowData.currentCapacity,
        clusterType: clusterType ?? ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        cloudId: bkCloudId,
        groupNum: localValue.machine_pair,
        shardNum,
        bkCloudId,
      };
      showClusterTargetPlan.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (obj: SpecResultInfo, capacity: number, targetInfo: TargetInfo) => {
    Object.assign(localValue, obj);
    futureCapacity.value = capacity;
    targetObj.value = targetInfo;
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
