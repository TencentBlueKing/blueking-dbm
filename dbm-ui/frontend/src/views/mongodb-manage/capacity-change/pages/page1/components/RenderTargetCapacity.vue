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
    <div v-if="!localValue">
      <DisableSelect
        ref="selectRef"
        :is-disabled="isDisabled"
        :placeholder="t('请选择')"
        :rules="rules"
        @click="handleClickSelect" />
    </div>
    <div
      v-else
      class="capacity-box"
      @click="handleClickSelect">
      <div class="display-content">
        <!-- <div class="item">
          <div class="item-title">
            {{ t('目标容量') }}：
          </div>
          <div class="item-content">
            <BkProgress
              :percent="60"
              :show-text="false"
              size="small"
              :stroke-width="14"
              type="circle"
              :width="16" />
            <span class="spec">{{ `(${123}G/${456}G)` }}</span>
          </div>
        </div> -->
        <div class="item">
          <div class="item-title">{{ t('目标资源规格') }}：</div>
          <div class="item-content">
            <RenderSpec
              :data="localValue"
              :hide-qps="!localValue?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('目标Shard节点规格') }}：</div>
          <div class="item-content">
            {{ localValue.shard_recommend.shard_spec }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('目标Shard节点数') }}：</div>
          <div class="item-content">
            {{ localValue.shard_node_count }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('目标Shard数量') }}：</div>
          <div class="item-content">
            {{ localValue.shard_num }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('目标机器组数') }}：</div>
          <div class="item-content">
            {{ localValue.machine_pair }}
          </div>
        </div>
        <div class="item">
          <div class="item-title">{{ t('目标机器数量') }}：</div>
          <div class="item-content">
            {{ localValue.machine_need_num }}
          </div>
        </div>
        <!-- <span style="margin-right: 5px;">{{ t('磁盘') }}:</span>
        <BkProgress
          color="#2DCB56"
          :percent="percent"
          :show-text="false"
          size="small"
          :stroke-width="18"
          type="circle"
          :width="20" /> -->
        <!-- <span class="percent">{{ percent > 100 ? 100 : percent }}%</span> -->
        <!-- <span class="spec">{{ `(${data.used}G/${data.total}G)` }}</span> -->
        <!-- <span class="spec">{{ `${localValue.cluster_capacity}G` }}</span> -->
        <!-- <span
          class="scale-percent"
          :style="{color: data.total > data.current ?
            '#EA3636' : '#2DCB56'}">{{ `(${changeObj.rate}%, ${changeObj.num}G)` }}</span> -->
        <!-- <span
          class="scale-percent"
          :style="{color: localValue.cluster_capacity > Number(props.rowData.targetCapacity?.current) ?
            '#EA3636' : '#2DCB56'}">{{ `(${changeObj.num}G)` }}</span> -->
      </div>
    </div>
  </BkLoading>
  <ChooseDeployPlan
    v-if="activeRowData"
    v-model="isShowSelector"
    :data="activeRowData"
    @confirm="handleChoosedTargetCapacity" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DisableSelect from '@components/render-table/columns/select-disable/index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ChooseDeployPlan, { type ClusterSpec, type Props as TargetPlanProps } from './ChooseDeployPlan.vue';
  import type { IDataRow } from './Row.vue';

  interface Props {
    isDisabled: boolean;
    rowData: IDataRow;
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<{
      shard_machine_group: number;
      shard_node_count: number;
      resource_spec: {
        mongodb: {
          spec_id: number;
          count: number;
        };
      };
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const selectRef = ref();
  const activeRowData = ref<TargetPlanProps['data']>();
  const localValue = shallowRef<ClusterSpec>();
  // const capacityObj = ref<CapacityNeed>();
  const isShowSelector = ref(false);

  // const percent = computed(() => {
  //   if (props.data) return Number(((props.data.used / props.data.total) * 100).toFixed(2));
  //   return 0;
  // });

  // const changeObj = computed(() => {
  //   const data = props.rowData;
  //   const currentTotal =  data.currentCapacity.total || 1;
  //   if (data && localValue.value) {
  //     const diff = localValue.value.cluster_capacity - currentTotal;
  //     const rate = ((diff / currentTotal) * 100).toFixed(2);
  //     if (diff < 0) {
  //       return {
  //         rate,
  //         num: diff,
  //       };
  //     }
  //     return {
  //       rate: `+${rate}`,
  //       num: `+${diff}`,
  //     };
  //   }
  //   return {
  //     rate: 0,
  //     num: 0,
  //   };
  // });

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('请选择目标容量'),
    },
  ];

  // 点击目标容量
  const handleClickSelect = () => {
    const { rowData } = props;
    if (rowData && rowData.clusterName) {
      activeRowData.value = rowData;
      isShowSelector.value = true;
    }
  };

  // 从侧边窗点击确认后触发
  const handleChoosedTargetCapacity = (obj: ClusterSpec) => {
    Object.assign(obj, {
      name: obj.spec_name,
    });
    localValue.value = obj;
  };

  defineExpose<Exposes>({
    async getValue() {
      await selectRef.value?.getValue();
      return Promise.resolve({
        shard_machine_group: localValue.value!.machine_pair,
        shard_node_count: props.rowData.shardNodeCount,
        resource_spec: {
          mongodb: {
            spec_id: localValue.value!.spec_id,
            count: localValue.value!.machine_pair * props.rowData.shardNodeCount,
          },
        },
      });
    },
  });
</script>
<style lang="less" scoped>
  .capacity-box {
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    border: 1px solid transparent;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

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
</style>
