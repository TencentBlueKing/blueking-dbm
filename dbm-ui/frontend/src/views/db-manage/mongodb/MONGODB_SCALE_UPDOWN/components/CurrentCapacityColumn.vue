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
        v-if="modelValue.id"
        class="current-capacity-block">
        <div class="info-item">
          <div class="item-title">{{ t('当前资源规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="spec"
              :hide-qps="!spec.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('当前Shard节点规格') }}：</div>
          <div class="item-content">
            {{ modelValue.shard_spec }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('当前Shard节点数') }}：</div>
          <div class="item-content">
            {{ modelValue.shard_node_count }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('当前Shard数量') }}：</div>
          <div class="item-content">
            {{ modelValue.shard_num }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('当前机器组数') }}：</div>
          <div class="item-content">
            {{ modelValue.mongodb_machine_pair }}
          </div>
        </div>
        <div class="info-item">
          <div class="item-title">{{ t('当前机器数量') }}：</div>
          <div class="item-content">
            {{ modelValue.mongodb_machine_num }}
          </div>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  const modelValue = defineModel<{
    id: number;
    mongodb: MongodbModel['mongodb'];
    mongodb_machine_num: number;
    mongodb_machine_pair: number;
    shard_node_count: number;
    shard_num: number;
    shard_spec: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const spec = computed(() => modelValue.value.mongodb?.[0].spec_config);
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
