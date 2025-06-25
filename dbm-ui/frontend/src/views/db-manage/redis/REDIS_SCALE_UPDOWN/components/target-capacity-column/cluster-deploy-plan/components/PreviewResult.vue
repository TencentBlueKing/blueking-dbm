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
  <div class="capacity-panel">
    <DiffInfoItem :label="t('容量')">
      <template #left>
        <span v-if="!diffState.current.capacity">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.current.capacity }}</span>
          G
        </template>
      </template>
      <template #right>
        <span v-if="!updateMode">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.target.capacity }}</span>
          G
          <ValueDiff
            :current-value="diffState.current.capacity"
            num-unit="G"
            :target-value="diffState.target.capacity" />
        </template>
      </template>
    </DiffInfoItem>
    <DiffInfoItem :label="t('资源规格')">
      <template #left>
        <span v-if="!diffState.current.spec.spec_id">--</span>
        <template v-else>
          <RenderSpec
            :data="diffState.current.spec"
            :hide-qps="!diffState.current.spec?.qps?.max"
            is-ignore-counts />
        </template>
      </template>
      <template #right>
        <span v-if="!updateMode">--</span>
        <template v-else>
          <RenderSpec
            :data="diffState.target.spec"
            :hide-qps="!diffState.target.spec?.qps?.max"
            is-ignore-counts />
        </template>
      </template>
    </DiffInfoItem>
    <DiffInfoItem :label="t('机器组数')">
      <template #left>
        <span v-if="!diffState.current.groupNum">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.current.groupNum }}</span>
        </template>
      </template>
      <template #right>
        <span v-if="!updateMode">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.target.groupNum }}</span>
          <ValueDiff
            :current-value="diffState.current.groupNum"
            :show-rate="false"
            :target-value="diffState.target.groupNum" />
        </template>
      </template>
    </DiffInfoItem>
    <DiffInfoItem :label="t('机器数量')">
      <template #left>
        <span v-if="!diffState.current.groupNum">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.current.groupNum * 2 }}</span>
        </template>
      </template>
      <template #right>
        <span v-if="!updateMode">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.target.groupNum * 2 }}</span>
          <ValueDiff
            :current-value="diffState.current.groupNum * 2"
            :show-rate="false"
            :target-value="diffState.target.groupNum * 2" />
        </template>
      </template>
    </DiffInfoItem>
    <DiffInfoItem :label="t('集群分片数')">
      <template #left>
        <span v-if="!diffState.current.shardNum">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.current.clusterShardNum }}</span>
        </template>
      </template>
      <template #right>
        <span v-if="!updateMode">--</span>
        <template v-else>
          <span class="number-style">{{ diffState.target.clusterShardNum }}</span>
          <ValueDiff
            :current-value="diffState.current.clusterShardNum"
            :show-rate="false"
            :target-value="diffState.target.clusterShardNum" />
        </template>
      </template>
    </DiffInfoItem>
    <DiffInfoItem :right-label="t('变更方式')">
      <template #right>
        {{ !updateMode ? '--' : updateMode === 'keep_current_machines' ? t('原地变更') : t('替换变更') }}
      </template>
    </DiffInfoItem>
  </div>
</template>
<script setup lang="tsx">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type RedisModel from '@services/model/redis/redis';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  import RenderSpec from '../../../render-spec/Index.vue';

  import DiffInfoItem from './DiffInfoItem.vue';

  interface Props {
    cluster: RedisModel;
    targetInfo: (typeof diffState)['target'];
    updateInfo: {
      capacity_update_type: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const init = () => ({
    capacity: 0,
    clusterShardNum: 0,
    clusterStats: {
      in_use: 0,
      total: 0,
      used: 0,
    },
    groupNum: 0,
    shardNum: 0,
    spec: {
      cpu: {
        max: 1,
        min: 0,
      },
      mem: {
        max: 1,
        min: 0,
      },
      qps: {
        max: 1,
        min: 0,
      },
      spec_id: 0,
      spec_name: '',
      storage_spec: [] as ComponentProps<typeof RenderSpec>['data']['storage_spec'],
    },
  });

  const diffState = reactive({
    current: init(),
    target: init(),
  });
  const updateMode = ref('');

  watch(
    () => props.cluster,
    () => {
      if (props.cluster.id) {
        diffState.current = {
          capacity: props.cluster.cluster_capacity,
          clusterShardNum: props.cluster.cluster_shard_num,
          clusterStats: props.cluster.cluster_stats,
          groupNum: props.cluster.machine_pair_cnt,
          shardNum: props.cluster.cluster_shard_num / props.cluster.machine_pair_cnt,
          spec: props.cluster.cluster_spec,
        };
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.updateInfo.capacity_update_type,
    () => {
      if (props.updateInfo.capacity_update_type === '') {
        diffState.target = init();
      } else {
        diffState.target = props.targetInfo;
      }
      updateMode.value = props.updateInfo.capacity_update_type;
    },
  );
</script>
<style lang="less" scoped>
  .capacity-panel {
    width: 880px;
    padding: 16px;
    background: #fafbfd;
  }

  .number-style {
    margin: 0 2px;
    font-size: 12px;
    font-weight: 700;
    color: #313238;
  }
</style>
