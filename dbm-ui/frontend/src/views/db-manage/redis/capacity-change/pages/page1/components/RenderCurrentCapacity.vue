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
      :class="{ 'default-display': !data.currentCapacity?.total }">
      <span
        v-if="!data.currentCapacity?.total"
        style="color: #c4c6cc">
        {{ t('选择集群后自动生成') }}
      </span>
      <div
        v-else
        class="display-content">
        <div class="item">
          <div class="item-title">{{ t('当前容量') }}：</div>
          <div class="item-content">
            <ClusterCapacityUsageRate :cluster-stats="data.clusterStats" />
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('资源规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="specData"
              :hide-qps="!specData?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('机器组数') }}：</div>
          <div class="item-content">
            {{ data.groupNum }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('机器数量') }}：</div>
          <div class="item-content">
            {{ (data.groupNum || 0) * 2 }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('分片数') }}：</div>
          <div class="item-content">
            {{ data.shardNum }}
          </div>
        </div>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import ClusterCapacityUsageRate from '@components/cluster-capacity-usage-rate/Index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data: IDataRow;
    isLoading: boolean;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const specData = computed(() => {
    const { spec } = props.data;
    if (spec) {
      return {
        name: spec.spec_name,
        cpu: spec.cpu,
        id: spec.spec_id,
        mem: spec.mem,
        qps: spec.qps,
        storage_spec: spec.storage_spec,
      };
    }
    return undefined;
  });
</script>

<style lang="less" scoped>
  .capacity-box {
    padding: 11px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .display-content {
      display: flex;
      flex-direction: column;

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

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }
</style>
