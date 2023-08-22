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
      v-if="!displayText"
      @click="handleClickSelect">
      <TableEditSelect
        ref="selectRef"
        disabled
        :list="[]"
        :placeholder="t('请选择')"
        :rules="rules" />
    </div>

    <div
      v-else
      class="capacity-box"
      @click="handleClickSelect">
      <span>{{ displayText }}</span>
      <DbIcon type="down-big" />
    </div>
    <Teleport to="body">
      <ChooseClusterTargetPlan
        :data="activeRowData"
        :is-show="showChooseClusterTargetPlan"
        :show-title-tag="false"
        :title="t('选择集群分片变更部署方案')"
        @click-cancel="() => showChooseClusterTargetPlan = false"
        @click-confirm="handleChoosedTargetCapacity" />
    </Teleport>
  </BkLoading>
</template>
<script lang="ts">
  export interface ExposeValue {
    spec_id: number,
    count: number,
    target_shard_num: number,
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { RedisClusterTypes } from '@services/model/redis/redis';
  import type { FilterClusterSpecItem } from '@services/resourceSpec';

  import TableEditSelect from '@views/redis/common/edit/Select.vue';

  import type { IDataRow } from '../Row.vue';

  import ChooseClusterTargetPlan, { type Props as TargetPlanProps } from './components/ClusterDeployPlan.vue';

  interface Props {
    rowData: IDataRow;
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<ExposeValue>
  }

  const props = withDefaults(defineProps<Props>(), {
    isLoading: false,
  });

  const { t } = useI18n();

  const displayText = ref('');
  const selectRef = ref();

  const showChooseClusterTargetPlan = ref(false);
  const activeRowData = ref<TargetPlanProps['data']>();

  const localValue = ref({
    spec_id: 0,
    count: 0,
    target_shard_num: 0,
  });

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择目标容量'),
    },
  ];

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (choosedObj: FilterClusterSpecItem) => {
    displayText.value = `${choosedObj.cluster_capacity}G_${choosedObj.qps.max}/s（${choosedObj.cluster_shard_num} 分片）`;
    localValue.value = {
      spec_id: choosedObj.spec_id,
      count: choosedObj.machine_pair,
      target_shard_num: choosedObj.cluster_shard_num,
    };
    showChooseClusterTargetPlan.value = false;
  };

  // 点击部署方案
  const handleClickSelect = () => {
    const { rowData } = props;
    if (rowData.srcCluster) {
      const { specConfig } = rowData;
      const obj = {
        targetCluster: rowData.srcCluster,
        currentSepc: t('cpus核memsGB_disksGB_QPS:qps', { cpus: specConfig.cpu.max, mems: specConfig.mem.max, disks: rowData.currentCapacity?.total, qps: specConfig.qps.max }),
        capacity: { total: rowData.currentCapacity?.total ?? 1, used: 0 },
        clusterType: rowData.clusterType as RedisClusterTypes,
        shardNum: rowData.currentShardNum,
      };
      activeRowData.value = obj;
      showChooseClusterTargetPlan.value = true;
    }
  };

  defineExpose<Exposes>({
    getValue() {
      if (!displayText.value) {
        return selectRef.value
          .getValue()
          .then(() => true);
      }
      return Promise.resolve(localValue.value);
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
