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
    <DisableSelect
      ref="selectRef"
      :data="displayText"
      :is-disabled="isDisabled || !targetClusterType"
      :placeholder="t('请选择')"
      :rules="rules"
      @click="handleClickSelect" />
  </BkLoading>
  <ChooseClusterTargetPlan
    :data="activeRowData"
    :is-show="showChooseClusterTargetPlan"
    :show-title-tag="false"
    :title="t('选择集群类型变更部署方案')"
    @click-cancel="() => (showChooseClusterTargetPlan = false)"
    @click-confirm="handleChoosedTargetCapacity" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import DisableSelect from '@components/render-table/columns/select-disable/index.vue';

  import ChooseClusterTargetPlan, {
    type CapacityNeed,
    type Props as TargetPlanProps,
    type SpecResultInfo,
  } from '@views/db-manage/redis/common/cluster-deploy-plan/Index.vue';

  import type { IDataRow } from './Row.vue';

  export interface ExposeValue {
    capacity: number;
    count: number;
    future_capacity: number;
    spec_id: number;
    target_shard_num: number;
  }

  interface Props {
    isDisabled: boolean;
    isLoading?: boolean;
    rowData: IDataRow;
    targetClusterType?: string;
  }

  interface Exposes {
    getValue: () => Promise<ExposeValue>;
  }

  const props = withDefaults(defineProps<Props>(), {
    isLoading: false,
    targetClusterType: '',
  });

  const { t } = useI18n();

  const displayText = ref('');
  const selectRef = ref();

  const showChooseClusterTargetPlan = ref(false);
  const activeRowData = ref<TargetPlanProps['data']>();

  const localValue = reactive({
    capacity: 0,
    count: 0,
    future_capacity: 0,
    spec_id: 0,
    target_shard_num: 0,
  });

  const rules = [
    {
      message: t('请选择目标容量'),
      validator: (value: string) => Boolean(value),
    },
  ];

  watchEffect(() => {
    localValue.target_shard_num = props.rowData.currentShardNum;
  });

  watchEffect(() => {
    localValue.count = props.rowData.groupNum;
  });

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (choosedObj: SpecResultInfo, capacity: CapacityNeed) => {
    displayText.value = `${choosedObj.cluster_capacity}G_（${choosedObj.cluster_shard_num} 分片）`;
    Object.assign(localValue, {
      capacity: capacity.current,
      count: choosedObj.machine_pair,
      future_capacity: capacity.future,
      spec_id: choosedObj.spec_id,
      target_shard_num: choosedObj.cluster_shard_num,
    });
    showChooseClusterTargetPlan.value = false;
  };

  // 点击部署方案
  const handleClickSelect = () => {
    if (!props.targetClusterType) {
      return;
    }
    const { rowData } = props;
    if (rowData.srcCluster) {
      const { specConfig } = rowData;
      const obj = {
        bkCloudId: rowData.bkCloudId,
        capacity: { total: rowData.currentCapacity?.total ?? 1, used: 0 },
        clusterType: props.targetClusterType as ClusterTypes,
        currentSepc: t('cpus核memsGB_disksGB_QPS:qps', {
          cpus: specConfig.cpu.max,
          disks: rowData.currentCapacity?.total,
          mems: specConfig.mem.max,
          qps: specConfig.qps.max,
        }),
        currentSepcId: `${specConfig.id}`,
        groupNum: localValue.count,
        shardNum: localValue.target_shard_num,
        targetCluster: rowData.srcCluster,
      };
      activeRowData.value = obj;
      showChooseClusterTargetPlan.value = true;
    }
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value
        .getValue()
        .then(() => localValue)
        .catch(() => Promise.reject(localValue));
    },
  });
</script>
<style lang="less" scoped>
  .capacity-box {
    display: flex;
    padding: 10px 16px;
    line-height: 20px;
    color: #63656e;
    justify-content: space-between;
    align-items: center;
  }
</style>
