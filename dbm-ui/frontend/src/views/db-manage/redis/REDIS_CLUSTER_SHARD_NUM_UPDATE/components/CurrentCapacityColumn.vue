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
    :label="t('当前容量')"
    :min-width="400">
    <EditableBlock :placeholder="t('选择集群后自动生成')">
      <div
        v-if="cluster.id"
        class="current-capacity-block">
        <div class="info-item">
          <div class="item-title">{{ t('Proxy 规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="proxySpec"
              :hide-qps="!proxySpec?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('Proxy 数量') }}：</div>
          <div class="item-content item-count">
            {{ cluster.proxy.length }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('使用率') }}：</div>
          <div class="item-content">
            <ClusterCapacityUsageRate :cluster-stats="cluster?.cluster_stats" />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('后端存储规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="backendSpec"
              :hide-qps="!backendSpec?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('机器组数') }}：</div>
          <div class="item-content item-count">
            {{ cluster.machine_pair_cnt }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('机器数量') }}：</div>
          <div class="item-content item-count">
            {{ cluster.machine_pair_cnt * 2 }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('分片数') }}：</div>
          <div class="item-content item-count">
            {{ cluster.cluster_shard_num }}
          </div>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';

  interface Props {
    cluster: {
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_stats: RedisModel['cluster_stats'];
      id: number;
      machine_pair_cnt: number;
      proxy: RedisModel['proxy'];
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const proxySpec = computed(() => props.cluster.proxy[0].spec_config);
  const backendSpec = computed(() => ({
    ...props.cluster.cluster_spec,
    name: props.cluster.cluster_spec.spec_name,
  }));
</script>

<style lang="less" scoped>
  .current-capacity-block {
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
