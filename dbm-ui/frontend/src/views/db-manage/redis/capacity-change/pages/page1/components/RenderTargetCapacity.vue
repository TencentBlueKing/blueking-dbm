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
  <BkLoading :loading="isLoading">
    <div
      v-overflow-tips
      class="capacity-box"
      @click="handleClickSelect">
      <DisableSelect
        v-if="!localValue || !activeRowData || !targetObj"
        ref="selectRef"
        :data="localValue?.spec_id"
        :is-disabled="isDisabled"
        :placeholder="t('请选择')"
        :rules="rules"
        @click="handleClickSelect" />
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
  </BkLoading>
  <ChooseClusterTargetPlan
    v-if="rowData"
    :cluster-id="rowData.clusterId"
    :cluster-stats="rowData.clusterStats"
    :data="activeRowData"
    hide-shard-column
    :is-show="showChooseClusterTargetPlan"
    :target-object="targetObj"
    :target-verison="targetVersion"
    :title="t('选择集群容量变更部署方案')"
    @click-cancel="() => (showChooseClusterTargetPlan = false)"
    @click-confirm="handleChoosedTargetCapacity"
    @target-stats-change="handleTargetStatsChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel, { RedisClusterTypes } from '@services/model/redis/redis';
  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';

  import ClusterCapacityUsageRate from '@components/cluster-capacity-usage-rate/Index.vue';
  import DisableSelect from '@components/render-table/columns/select-disable/index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';
  import { AffinityType } from '@views/db-manage/redis/common/types';

  import { convertStorageUnits } from '@utils';

  import ChooseClusterTargetPlan, { type Props as TargetPlanProps, type TargetInfo } from './ClusterDeployPlan.vue';
  import type { IDataRow } from './Row.vue';

  interface Props {
    isDisabled: boolean;
    rowData?: IDataRow;
    isLoading?: boolean;
    targetVersion?: string;
  }

  interface Exposes {
    getValue: () => Promise<{
      shard_num: number;
      group_num: number;
      capacity: number;
      future_capacity: number;
      resource_spec: {
        backend_group: {
          spec_id: number;
          count: number;
          affinity: AffinityType;
        };
      };
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const selectRef = ref();
  const activeRowData = ref<TargetPlanProps['data']>();
  const showChooseClusterTargetPlan = ref(false);
  const localValue = shallowRef<ClusterSpecModel>();
  const futureCapacity = ref(1);
  const targetObj = ref<TargetInfo>();
  const targetClusterStats = ref<RedisModel['cluster_stats']>({} as Record<string, never>);

  const currentCapacity = computed(() => {
    if (!props.rowData || _.isEmpty(props.rowData?.clusterStats)) {
      return props.rowData?.currentCapacity?.total ?? 0;
    }
    return convertStorageUnits(props.rowData.clusterStats.total, 'B', 'GB');
  });

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择目标容量'),
    },
  ];

  // 点击目标容量
  const handleClickSelect = () => {
    if (props.isDisabled) {
      return;
    }
    const { rowData } = props;
    if (rowData && rowData.targetCluster) {
      const { spec = {} as NonNullable<IDataRow['spec']> } = rowData;
      const obj = {
        targetCluster: rowData.targetCluster,
        currentSepc: {
          name: spec.spec_name ?? '',
          cpu: spec.cpu,
          id: spec.spec_id,
          mem: spec.mem,
          qps: spec.qps,
          storage_spec: spec.storage_spec,
        },
        capacity: rowData.currentCapacity ?? { used: 0, total: 1 },
        clusterType: rowData.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance,
        groupNum: rowData.groupNum ?? 0,
        shardNum: rowData.shardNum ?? 0,
      };
      activeRowData.value = obj;
      showChooseClusterTargetPlan.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (obj: ClusterSpecModel, capacity: number, targetInfo: TargetInfo) => {
    localValue.value = obj;
    futureCapacity.value = capacity;
    targetObj.value = targetInfo;
    showChooseClusterTargetPlan.value = false;
  };

  const handleTargetStatsChange = (value: RedisModel['cluster_stats']) => {
    targetClusterStats.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      if (!localValue.value) {
        return selectRef.value.getValue().then(() => true);
      }
      return Promise.resolve({
        shard_num: localValue.value.cluster_shard_num, // props.rowData!.shardNum
        group_num: localValue.value.machine_pair, // targetObj.value!.requireMachineGroupNum,
        capacity: futureCapacity.value ?? 1,
        future_capacity: futureCapacity.value ?? 1,
        update_mode: targetObj.value?.updateMode,
        resource_spec: {
          backend_group: {
            spec_id: localValue.value.spec_id,
            count: targetObj.value!.requireMachineGroupNum, // 机器实际需要申请的组数
            affinity: AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
          },
        },
      });
    },
  });
</script>
<style lang="less" scoped>
  .capacity-box {
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    border: 1px solid transparent;

    .content {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: #63656e;

      .percent {
        margin-left: 4px;
        font-size: 12px;
        font-weight: bold;
        color: #313238;
      }

      .spec {
        margin-left: 2px;
        font-size: 12px;
        // color: #979BA5;
      }

      .scale-percent {
        margin-left: 5px;
        font-size: 12px;
        font-weight: bold;
      }
    }

    .display-content {
      display: flex;
      flex-direction: column;
      padding: 11px 16px;

      .content-item {
        display: flex;
        width: 100%;

        .item-title {
          width: 60px;
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
