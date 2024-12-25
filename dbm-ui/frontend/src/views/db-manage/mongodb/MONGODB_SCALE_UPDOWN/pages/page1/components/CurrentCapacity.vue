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
  <div class="current-capacity-block">
    <div class="info-item">
      <div class="item-title">{{ t('当前资源规格') }}：</div>
      <div class="item-content">
        <RenderSpec
          :data="spec"
          :hide-qps="!spec?.qps.max"
          is-ignore-counts />
      </div>
    </div>
    <div class="info-item">
      <div class="item-title">{{ t('当前Shard节点规格') }}：</div>
      <div class="item-content">
        {{ data?.shard_spec }}
      </div>
    </div>
    <div class="info-item">
      <div class="item-title">{{ t('当前Shard节点数') }}：</div>
      <div class="item-content">
        {{ data?.shard_node_count }}
      </div>
    </div>
    <div class="info-item">
      <div class="item-title">{{ t('当前Shard数量') }}：</div>
      <div class="item-content">
        {{ data?.shard_num }}
      </div>
    </div>
    <div class="info-item">
      <div class="item-title">{{ t('当前机器组数') }}：</div>
      <div class="item-content">
        {{ data?.mongodb_machine_pair }}
      </div>
    </div>
    <div class="info-item">
      <div class="item-title">{{ t('当前机器数量') }}：</div>
      <div class="item-content">
        {{ data?.mongodb_machine_num }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  interface Props {
    data: {
      shard_spec?: string;
      shard_node_count?: number;
      shard_num?: number;
      mongodb_machine_pair?: number;
      mongodb_machine_num?: number;
    };
    spec?: MongodbModel['mongodb'][number]['spec_config'];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .current-capacity-block {
    display: flex;
    flex-direction: column;

    .info-item {
      display: flex;
      width: 100%;

      .item-title {
        width: 125px;
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
    }
  }
</style>
