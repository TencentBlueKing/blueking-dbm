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
    field="cluster_capacity"
    :label="t('当前容量')"
    :min-width="150">
    <div class="capacity-box">
      <div
        v-if="cluster?.cluster_stats?.total"
        class="display-content">
        <div class="item">
          <div class="item-title">{{ t('当前容量') }}：</div>
          <div class="item-content">
            <ClusterCapacityUsageRate :cluster-stats="cluster?.cluster_stats" />
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('资源规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="cluster?.cluster_spec"
              :hide-qps="!cluster?.cluster_spec?.qps?.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('机器组数') }}：</div>
          <div class="item-content">
            {{ cluster.group_num }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('机器数量') }}：</div>
          <div class="item-content">
            {{ cluster.group_num * 2 }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('分片数') }}：</div>
          <div class="item-content">
            {{ cluster.shard_num }}
          </div>
        </div>
      </div>
      <EditableBlock
        v-else
        :placeholder="t('自动生成')" />
    </div>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';

  interface Props {
    cluster: {
      cluster_spec: RedisModel['cluster_spec'];
      cluster_stats: RedisModel['cluster_stats'];
      group_num: number;
      shard_num: number;
    };
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
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
