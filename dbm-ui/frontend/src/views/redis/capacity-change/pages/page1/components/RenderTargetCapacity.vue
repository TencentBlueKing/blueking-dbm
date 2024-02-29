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
    <div v-if="!localValue">
      <DisableSelect
        ref="selectRef"
        :is-disabled="isDisabled"
        :placeholder="t('请选择')"
        :rules="rules"
        @click="handleClickSelect" />
    </div>

    <div
      v-else
      class="capacity-box"
      @click="handleClickSelect">
      <div class="content">
        <!-- <span style="margin-right: 5px;">{{ t('磁盘') }}:</span>
        <BkProgress
          color="#2DCB56"
          :percent="percent"
          :show-text="false"
          size="small"
          :stroke-width="18"
          type="circle"
          :width="20" /> -->
        <!-- <span class="percent">{{ percent > 100 ? 100 : percent }}%</span> -->
        <!-- <span class="spec">{{ `(${data.used}G/${data.total}G)` }}</span> -->
        <span class="spec">{{ `${localValue.cluster_capacity}G` }}</span>
        <!-- <span
          class="scale-percent"
          :style="{color: data.total > data.current ?
            '#EA3636' : '#2DCB56'}">{{ `(${changeObj.rate}%, ${changeObj.num}G)` }}</span> -->
        <span
          class="scale-percent"
          :style="{
            color: localValue.cluster_capacity > Number(props.rowData?.targetCapacity?.current) ? '#EA3636' : '#2DCB56',
          }">
          {{ `(${changeObj.num}G)` }}
        </span>
      </div>
    </div>
  </BkLoading>
  <ChooseClusterTargetPlan
    :data="activeRowData"
    is-same-shard-num
    :is-show="showChooseClusterTargetPlan"
    :title="t('选择集群容量变更部署方案')"
    @click-cancel="() => (showChooseClusterTargetPlan = false)"
    @click-confirm="handleChoosedTargetCapacity" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { RedisClusterTypes } from '@services/model/redis/redis';
  import RedisClusterSpecModel from '@services/model/resource-spec/redis-cluster-sepc';

  import DisableSelect from '@components/render-table/columns/select-disable/index.vue';

  import ChooseClusterTargetPlan, {
    type CapacityNeed,
    type Props as TargetPlanProps,
  } from '@views/redis/common/cluster-deploy-plan/Index.vue';
  import { AffinityType } from '@views/redis/common/types';

  import type { IDataRow } from './Row.vue';

  interface Props {
    isDisabled: boolean;
    rowData?: IDataRow;
    isLoading?: boolean;
  }


  interface Exposes {
    getValue: () => Promise<boolean>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const selectRef = ref();
  const activeRowData = ref<TargetPlanProps['data']>();
  const showChooseClusterTargetPlan = ref(false);
  const localValue = shallowRef<RedisClusterSpecModel>();
  const capacityObj = ref<CapacityNeed>();

  // const percent = computed(() => {
  //   if (props.data) return Number(((props.data.used / props.data.total) * 100).toFixed(2));
  //   return 0;
  // });

  const changeObj = computed(() => {
    const data = props.rowData;
    const currentTotal =  data?.currentCapacity?.total || 1;
    if (data && localValue.value) {
      const diff = localValue.value.cluster_capacity - currentTotal;
      const rate = ((diff / currentTotal) * 100).toFixed(2);
      if (diff < 0) {
        return {
          rate,
          num: diff,
        };
      }
      return {
        rate: `+${rate}`,
        num: `+${diff}`,
      };
    }
    return {
      rate: 0,
      num: 0,
    };
  });

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择目标容量'),
    },
  ];

  // 点击目标容量
  const handleClickSelect = () => {
    const { rowData } = props;
    if (rowData && rowData.targetCluster) {
      const obj = {
        targetCluster: rowData.targetCluster,
        currentSepc: rowData.currentSepc ?? '',
        capacity: rowData.currentCapacity ?? { used: 0, total: 1 },
        clusterType: rowData.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance,
        shardNum: rowData.shardNum ?? 0,
      };
      activeRowData.value = obj;
      showChooseClusterTargetPlan.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (obj: RedisClusterSpecModel, capacity: CapacityNeed) => {
    localValue.value = obj;
    capacityObj.value = capacity;
    showChooseClusterTargetPlan.value = false;
  };

  defineExpose<Exposes>({
    getValue() {
      if (!localValue.value) {
        return selectRef.value
          .getValue()
          .then(() => true);
      }
      return Promise.resolve({
        shard_num: localValue.value.cluster_shard_num,
        group_num: localValue.value.machine_pair,
        capacity: capacityObj.value?.current ?? 1,
        future_capacity: capacityObj.value?.future ?? 1,
        resource_spec: {
          backend_group: {
            spec_id: localValue.value.spec_id,
            count: localValue.value.machine_pair, // 机器组数
            affinity: AffinityType.CROS_SUBZONE, // 暂时固定 'CROS_SUBZONE',
          },
        },
      });
    },
  });
</script>
<style lang="less" scoped>
  .capacity-box {
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    border: 1px solid transparent;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

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
  }
</style>
