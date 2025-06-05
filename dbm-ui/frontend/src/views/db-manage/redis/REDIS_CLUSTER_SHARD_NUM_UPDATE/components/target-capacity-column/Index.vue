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
    field="target_capacity"
    :label="t('新部署方案')"
    :min-width="400"
    required>
    <template #head>
      <BkPopover
        :content="t('将会部署新的集群以进行集群变更')"
        placement="top"
        theme="dark">
        <span class="edit-target-spec-label-tip">{{ t('新部署方案') }}</span>
      </BkPopover>
    </template>
    <EditableBlock
      :placeholder="t('请选择')"
      style="cursor: pointer"
      @click="handleClickSelect">
      <div
        v-if="modelValue.backend_group.id"
        class="target-capacity-block">
        <div class="info-item">
          <div class="item-title">{{ t('Proxy 规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="targetProxySpecInfo"
              :hide-qps="!targetProxySpecInfo?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('Proxy 数量') }}：</div>
          <div class="item-content item-count">
            {{ targetProxySpecInfo?.count || 0 }}
            <ValueDiff
              :current-value="cluster.proxy.length"
              :show-rate="false"
              :target-value="targetProxySpecInfo?.count || 0" />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('使用率') }}：</div>
          <div class="item-content">
            <ClusterCapacityUsageRate :cluster-stats="targetClusterStats" />
            <ValueDiff
              :current-value="convertStorageUnits(cluster.cluster_stats.total, 'B', 'GB')"
              num-unit="G"
              :target-value="modelValue.future_capacity" />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('后端存储规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="targetBackendSpecInfo"
              :hide-qps="!targetBackendSpecInfo?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('机器组数') }}：</div>
          <div class="item-content item-count">
            {{ modelValue.backend_group.count }}
            <ValueDiff
              :current-value="cluster.machine_pair_cnt"
              :show-rate="false"
              :target-value="modelValue.backend_group.count" />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('机器数量') }}：</div>
          <div class="item-content item-count">
            {{ modelValue.backend_group.count * 2 }}
            <ValueDiff
              :current-value="cluster.machine_pair_cnt * 2"
              :show-rate="false"
              :target-value="modelValue.backend_group.count * 2" />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('分片数') }}：</div>
          <div class="item-content item-count">
            {{ modelValue.cluster_shard_num }}
            <ValueDiff
              :current-value="cluster.cluster_shard_num"
              :show-rate="false"
              :target-value="modelValue.cluster_shard_num" />
          </div>
        </div>
      </div>
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
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { ClusterTypes } from '@common/const';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  import { convertStorageUnits } from '@utils';

  import ChooseClusterTargetPlan, {
    type CapacityNeed,
    type SpecResultInfo,
  } from './components/ChooseClusterTargetPlan.vue';

  interface Props {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      city_code: string;
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_stats: RedisModel['cluster_stats'];
      cluster_type: string;
      id: number;
      machine_pair_cnt: number;
      master_domain: string;
      proxy: RedisModel['proxy'];
    };
    title: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    backend_group: {
      count: number;
      id: number;
    };
    capacity: number;
    cluster_shard_num: number;
    future_capacity: number;
    proxy: {
      count: number;
      id: number;
    };
  }>({
    required: true,
  });

  const { t } = useI18n();

  // const displayText = ref('');
  const disabledConfirm = ref(false);

  const targetProxySpecInfo = shallowRef<ComponentProps<typeof RenderSpec>['data']>();
  const targetBackendSpecInfo = shallowRef<ComponentProps<typeof RenderSpec>['data']>();

  const showChooseClusterTargetPlan = ref(false);

  const rules = [
    {
      message: t('部署方案不能为空'),
      required: true,
      trigger: 'change',
      validator: (value: UnwrapRef<typeof modelValue>) => Boolean(value.backend_group.id && value.proxy.id),
    },
    {
      message: t('目标分片数不能与当前分片数相同'),
      trigger: 'change',
      validator: () => props.cluster.cluster_shard_num !== modelValue.value.cluster_shard_num,
    },
  ];

  // watchEffect(() => {
  //   modelValue.value.cluster_shard_num = props.cluster.cluster_shard_num || 0;
  // });

  const targetClusterStats = computed(() => {
    let stats = {} as RedisModel['cluster_stats'];
    if (!_.isEmpty(props.cluster.cluster_stats)) {
      const { used = 0 } = props.cluster.cluster_stats;
      const targetTotal = convertStorageUnits(modelValue.value.future_capacity ?? 0, 'GB', 'B');

      stats = {
        in_use: Number(((used / targetTotal) * 100).toFixed(2)),
        total: targetTotal,
        used,
      };
    }

    // emits('targetStatsChange', stats);
    return stats;
  });

  watch(
    () => props.cluster.cluster_type,
    () => {
      if (props.cluster.cluster_type) {
        modelValue.value.backend_group.count = [
          ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ].includes(props.cluster.cluster_type as ClusterTypes)
          ? 3
          : 1;
      }
    },
    {
      immediate: true,
    },
  );

  const disabledMethod = () => {
    if (!props.cluster.id) {
      return t('请先选择集群');
    }
    return false;
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (choosedObj: SpecResultInfo, capacity: CapacityNeed) => {
    // displayText.value = `${choosedObj.cluster_capacity}G（${choosedObj.cluster_shard_num} 分片）`;
    Object.assign(modelValue.value, {
      backend_group: {
        count: choosedObj.backend_spec?.count,
        id: choosedObj.backend_spec?.id,
      },
      capacity: capacity.current,
      cluster_shard_num: choosedObj.cluster_shard_num,
      future_capacity: capacity.future,
      proxy: {
        count: choosedObj.proxy_spec?.count,
        id: choosedObj.proxy_spec?.id,
      },
    });
    targetProxySpecInfo.value = choosedObj.proxy_spec;
    targetBackendSpecInfo.value = choosedObj.backend_spec;
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

  .target-capacity-block {
    display: flex;
    flex-direction: column;

    .info-item {
      display: flex;
      width: 100%;

      .item-title {
        width: 90px;
        text-align: right;
      }

      .item-content {
        flex: 1;
        display: flex;
        align-items: center;

        :deep(.render-spec-box) {
          height: 22px;
          padding: 0;
        }
      }

      .item-count {
        font-weight: bolder;
      }
    }
  }
</style>
