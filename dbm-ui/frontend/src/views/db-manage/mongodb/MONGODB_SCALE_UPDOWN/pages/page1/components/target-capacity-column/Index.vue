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
  <EditableTableColumn
    field="target_capacity"
    :label="t('目标容量')"
    :min-width="400"
    required>
    <EditBlock :placeholder="t('请选择')">
      <div
        class="target-capacity"
        @click="handleClickSelect">
        <div v-if="!modelValue">
          <div class="placeholder-text">{{ t('请选择') }}</div>
        </div>
        <div
          v-else
          class="capacity-box">
          <div class="display-content">
            <div class="item">
              <div class="item-title">{{ t('目标资源规格') }}：</div>
              <div class="item-content">
                <RenderSpec
                  :data="selectRow"
                  :hide-qps="!selectRow?.qps.max"
                  is-ignore-counts />
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标Shard节点规格') }}：</div>
              <div class="item-content">
                {{ selectRow?.shard_recommend.shard_spec }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标Shard节点数') }}：</div>
              <div class="item-content">
                {{ selectRow?.shard_node_count }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标Shard数量') }}：</div>
              <div class="item-content">
                {{ selectRow?.shard_num }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标机器组数') }}：</div>
              <div class="item-content">
                {{ selectRow?.machine_pair }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标机器数量') }}：</div>
              <div class="item-content">
                {{ selectRow?.machine_need_num }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </EditBlock>
  </EditableTableColumn>
  <ChooseDeployPlan
    v-if="data.id"
    v-model="isShowSelector"
    :data="data as Required<typeof data>"
    @confirm="handleChoosedTargetCapacity" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import { Block as EditBlock, Column as EditableTableColumn } from '@components/editable-table/Index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ChooseDeployPlan, { type ClusterSpec } from './components/ChooseDeployPlan.vue';

  interface Props {
    data: {
      id?: number;
      master_domain?: string;
      bk_cloud_id?: number;
      shard_num?: number;
      shard_node_count?: number;
      mongodb?: MongodbModel['mongodb'];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    shard_machine_group: number;
    shard_node_count: number;
    shards_num: number;
    resource_spec: {
      mongodb: {
        spec_id: number;
        count: number;
      };
    };
  }>();

  const { t } = useI18n();

  const selectRow = shallowRef<ClusterSpec>();
  const isShowSelector = ref(false);

  // 点击目标容量
  const handleClickSelect = () => {
    const { data } = props;
    if (data && data.master_domain) {
      isShowSelector.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (specRow: ClusterSpec) => {
    selectRow.value = specRow;
    modelValue.value = {
      shard_machine_group: specRow.machine_pair,
      shard_node_count: specRow.shard_node_count,
      shards_num: specRow.shard_num,
      resource_spec: {
        mongodb: {
          spec_id: specRow.spec_id,
          count: specRow.machine_pair * specRow.shard_node_count,
        },
      },
    };
  };
</script>

<style lang="less" scoped>
  .target-capacity {
    cursor: pointer;

    .placeholder-text {
      height: 120px;
      line-height: 120px;
      color: #c4c6cc;
    }

    .capacity-box {
      padding: 10px 16px;
      overflow: hidden;
      line-height: 20px;
      color: #63656e;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
      border: 1px solid transparent;

      .display-content {
        display: flex;
        flex-direction: column;

        .item {
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
  }
</style>
