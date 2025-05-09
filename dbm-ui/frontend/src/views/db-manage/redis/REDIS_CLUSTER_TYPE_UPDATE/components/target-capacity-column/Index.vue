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
    :append-rules="rules"
    :disabled-method="disabledMethod"
    field="target_capacity.spec_id"
    :label="t('新集群部署方案')"
    required
    :width="200">
    <template #head>
      <BkPopover
        :content="t('将会部署新的集群以进行集群变更')"
        placement="top"
        theme="dark">
        <span class="edit-target-spec-label-tip">{{ t('新集群部署方案') }}</span>
      </BkPopover>
    </template>
    <EditableBlock
      v-model="displayText"
      :placeholder="t('请选择')"
      style="cursor: pointer"
      @click="handleClickSelect">
    </EditableBlock>
  </EditableColumn>
  <DbSideslider
    v-if="cluster.id"
    v-model:is-show="showChooseClusterTargetPlan"
    :disabled-confirm="disabledConfirm"
    render-directive="show"
    :width="960">
    <template #header>
      {{ title }}
      【{{ cluster?.master_domain }}】
    </template>
    <ChooseClusterTargetPlan
      v-model:disabled-confirm="disabledConfirm"
      :cluster="cluster"
      :target-spec="modelValue"
      :title="t('选择集群分片变更部署方案')"
      @click-cancel="() => (showChooseClusterTargetPlan = false)"
      @click-confirm="handleChoosedTargetCapacity">
    </ChooseClusterTargetPlan>
  </DbSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import ChooseClusterTargetPlan, {
    type CapacityNeed,
    type SpecResultInfo,
  } from './components/ChooseClusterTargetPlan.vue';

  interface Props {
    cluster: {
      bk_cloud_id: number;
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_type: string;
      id: number;
      machine_pair_cnt: number;
      master_domain: string;
    };
    title: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    capacity: number;
    cluster_shard_num: number;
    count: number;
    future_capacity: number;
    spec_id: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const displayText = ref('');
  const disabledConfirm = ref(false);

  const showChooseClusterTargetPlan = ref(false);

  const rules = [
    {
      message: t('部署方案不能为空'),
      required: true,
      trigger: 'change',
      validator: (value: number) => value > 0,
    },
    {
      message: t('目标分片数不能与当前分片数相同'),
      trigger: 'change',
      validator: () => props.cluster.cluster_shard_num !== modelValue.value.cluster_shard_num,
    },
  ];

  watchEffect(() => {
    modelValue.value.cluster_shard_num = props.cluster.cluster_shard_num || 0;
  });

  watchEffect(() => {
    modelValue.value.count = props.cluster.machine_pair_cnt || 0;
  });

  const disabledMethod = () => (props.cluster.id ? false : t('请先选择集群'));

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (choosedObj: SpecResultInfo, capacity: CapacityNeed) => {
    displayText.value = `${choosedObj.cluster_capacity}G（${choosedObj.cluster_shard_num} 分片）`;
    Object.assign(modelValue.value, {
      capacity: capacity.current,
      cluster_shard_num: choosedObj.cluster_shard_num,
      count: choosedObj.machine_pair,
      future_capacity: capacity.future,
      spec_id: choosedObj.spec_id,
    });
    showChooseClusterTargetPlan.value = false;
  };

  const handleClickSelect = () => {
    showChooseClusterTargetPlan.value = true;
  };
</script>
<style lang="less" scoped>
  .edit-target-spec-label-tip {
    border-bottom: 1px dashed #979ba5;
  }
</style>
