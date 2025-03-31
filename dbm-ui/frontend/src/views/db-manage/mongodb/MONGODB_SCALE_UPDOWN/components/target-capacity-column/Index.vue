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
    ref="editableColumnRef"
    :append-rules="rules"
    :disabled-method="columnDisabledMethod"
    field="target_capacity.resource_spec.mongodb.spec_id"
    :label="t('目标容量')"
    :min-width="400"
    required>
    <EditableBlock>
      <div
        class="target-capacity"
        @click="handleClickSelect">
        <div v-if="!modelValue.shards_num">
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
                  :data="targetSpecData!"
                  :hide-qps="!targetSpecData?.qps?.max"
                  is-ignore-counts />
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标Shard节点规格') }}：</div>
              <div class="item-content">
                {{ targetSpecData?.shard_spec }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标Shard节点数') }}：</div>
              <div class="item-content">
                {{ modelValue.shard_node_count }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标Shard数量') }}：</div>
              <div class="item-content">
                {{ modelValue.shards_num }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标机器组数') }}：</div>
              <div class="item-content">
                {{ modelValue.shard_machine_group }}
              </div>
            </div>
            <div class="item">
              <div class="item-title">{{ t('目标机器数量') }}：</div>
              <div class="item-content">
                {{ modelValue.shard_node_count * modelValue.shard_machine_group }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
  <DbSideslider
    v-if="cluster"
    v-model:is-show="isShowSelector"
    :disabled-confirm="!isCapacityChange"
    :width="960">
    <template #header>
      <span>
        {{ t('MongoDB 集群容量变更【xxx】', [cluster.master_domain]) }}
        <BkTag theme="info">
          {{ t('存储层') }}
        </BkTag>
      </span>
    </template>
    <SpecPlan
      v-model:is-change="isCapacityChange"
      :cluster-data="cluster"
      @confirm="handleChoosedTargetCapacity" />
  </DbSideslider>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';

  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import SpecPlan from './components/SpecPlan.vue';

  interface Props {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_name: string;
      cluster_type: string;
      id: number;
      master_domain: string;
      mongodb: MongodbModel['mongodb'];
      shard_node_count: number;
      shard_num: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    resource_spec: {
      mongodb: {
        count: number;
        spec_id: number;
      };
    };
    shard_machine_group: number;
    shard_node_count: number;
    shards_num: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const editableColumnRef = useTemplateRef('editableColumnRef');

  const isShowSelector = ref(false);
  const isCapacityChange = ref(false);

  const targetSpecData = shallowRef<{ shard_spec: string } & ComponentProps<typeof RenderSpec>['data']>();

  const rules = [
    {
      message: t('目标容量不能为空'),
      required: true,
      trigger: 'change',
      validator: (value: number) => value > 0,
    },
  ];

  const columnDisabledMethod = ({ cluster }: { cluster: Props['cluster'] }) =>
    cluster.master_domain ? false : t('请先选择或输入集群');

  // 点击目标容量
  const handleClickSelect = () => {
    if (props.cluster.master_domain) {
      isShowSelector.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (
    inputInfo: {
      shard_machine_group: number;
      shard_node_count: number;
      shards_num: number;
      spec_id: number;
    },
    specInfo: {
      shard_recommend?: {
        shard_num: number;
        shard_spec: string;
      };
    } & Pick<ClusterSpecModel, 'cpu' | 'mem' | 'spec_name' | 'storage_spec' | 'qps'>,
  ) => {
    modelValue.value = {
      resource_spec: {
        mongodb: {
          count: inputInfo.shard_machine_group * inputInfo.shard_node_count,
          spec_id: inputInfo.spec_id,
        },
      },
      shard_machine_group: inputInfo.shard_machine_group,
      shard_node_count: inputInfo.shard_node_count,
      shards_num: inputInfo.shards_num,
    };
    if (specInfo) {
      targetSpecData.value = {
        cpu: specInfo.cpu,
        mem: specInfo.mem,
        name: specInfo.spec_name,
        qps: specInfo.qps,
        shard_spec: specInfo?.shard_recommend?.shard_spec || '--',
        storage_spec: specInfo.storage_spec,
      };
    }

    nextTick(() => {
      editableColumnRef.value!.validate();
    });
  };
</script>

<style lang="less" scoped>
  .target-capacity {
    cursor: pointer;

    .placeholder-text {
      height: 100%;
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
