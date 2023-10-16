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
  <BkSideslider
    :before-close="handleClose"
    :is-show="isShow"
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ title }}
        【{{ data?.targetCluster }}】
        <BkTag
          v-if="showTitleTag"
          theme="info">
          {{ t('存储层') }}
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="capacity-panel">
        <div class="panel-row">
          <div class="column">
            <div class="title">
              {{ t('当前资源规格') }}：
            </div>
            <div class="content">
              {{ data?.currentSepc }}
            </div>
          </div>
          <div class="column">
            <div class="title">
              {{ t('变更后的规格') }}：
            </div>
            <div class="content">
              <span v-if="targetSepc">{{ targetSepc }}</span>
              <span
                v-else
                style="color: #C4C6CC;">{{ t('请先选择部署方案') }}</span>
            </div>
          </div>
        </div>
        <div
          class="panel-row"
          style="margin-top: 12px;">
          <div class="column">
            <div
              class="title"
              style="min-width: 70px;">
              {{ t('当前总容量') }}：
            </div>
            <div class="content">
              <!-- <BkProgress
                color="#EA3636"
                :percent="35"
                :show-text="false"
                size="small"
                :stroke-width="16"
                type="circle"
                :width="15" />
              <span class="percent">{{ currentPercent }}%</span> -->
              <span class="spec">{{ currentSpec }}</span>
            </div>
          </div>
          <div class="column">
            <div
              class="title"
              style="min-width: 82px;">
              {{ t('变更后总容量') }}：
            </div>
            <div class="content">
              <template v-if="targetSepc">
                <!-- <BkProgress
                  color="#2DCB56"
                  :percent="targetPercent"
                  :show-text="false"
                  size="small"
                  :stroke-width="16"
                  type="circle"
                  :width="15" />
                <span class="percent">{{ targetPercent }}%</span> -->
                <!-- <span class="spec">{{ `(${data.capacity.used}G/${targetCapacity.total}G)` }}</span> -->
                <span class="spec">{{ `${targetCapacity.total}G` }}</span>
                <!-- <span
                  class="scale-percent"
                  :class="[targetCapacity.total > targetCapacity.current ? 'positive' : 'negtive']">
                  {{ `(${changeObj.rate}%, ${changeObj.num}G)` }}
                </span> -->
                <span
                  class="scale-percent"
                  :class="[targetCapacity.total > targetCapacity.current ? 'positive' : 'negtive']">
                  {{ `(${changeObj.num}G)` }}
                </span>
              </template>
              <span
                v-else
                style="color: #C4C6CC;">{{ t('请先选择部署方案') }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="select-group">
        <div class="select-box">
          <div class="title-spot">
            {{ t('目标集群容量需求') }}<span class="required" />
          </div>
          <div class="input-box">
            <BkInput
              class="mb10 num-input"
              :min="0"
              :model-value="capacityNeed"
              size="small"
              type="number"
              @blur="handleSearchClusterSpec"
              @change="(value) => capacityNeed = Number(value)" />
            <div class="uint">
              G
            </div>
          </div>
        </div>
        <div class="select-box">
          <div class="title-spot">
            {{ t('未来集群容量需求') }}<span class="required" />
          </div>
          <div class="input-box">
            <BkInput
              class="mb10 num-input"
              :min="0"
              :model-value="capacityFutureNeed"
              size="small"
              type="number"
              @blur="handleSearchClusterSpec"
              @change="(value) => capacityFutureNeed = Number(value)" />
            <div class="uint">
              G
            </div>
          </div>
          <div
            v-if="isShowGreaterTip"
            class="gt-tip">
            <span>{{ t('未来容量必须大于等于目标容量') }}</span>
          </div>
        </div>
      </div>
      <div class="deploy-box">
        <div class="title-spot">
          {{ t('集群部署方案') }}<span class="required" />
        </div>
        <BkLoading :loading="isTableLoading">
          <DbOriginalTable
            class="deploy-table"
            :columns="columns"
            :data="tableData"
            @column-sort="handleColumnSort"
            @row-click.stop="handleRowClick">
            <template #empty>
              <p
                v-if="!capacityNeed || !capacityFutureNeed"
                style="width: 100%; line-height: 128px; text-align: center;">
                <DbIcon
                  class="mr-4"
                  type="attention" />
                <span>{{ t('请先设置容量') }}</span>
              </p>
              <BkException
                v-else
                :description="t('无匹配的资源规格_请先修改容量设置')"
                scene="part"
                style="font-size: 12px;"
                type="empty" />
            </template>
          </DbOriginalTable>
        </BkLoading>
      </div>
    </div>

    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!isAbleSubmit"
        :loading="isConfirmLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isConfirmLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { RedisClusterTypes } from '@services/model/redis/redis';
  import RedisClusterSpecModel from '@services/model/resource-spec/redis-cluster-sepc';
  import { getFilterClusterSpec } from '@services/resourceSpec';

  import { useBeforeClose } from '@hooks';

  export interface Props {
    isShow?: boolean;
    isSameShardNum?: boolean;
    data?: {
      targetCluster: string,
      currentSepc: string,
      capacity: {
        total: number,
        used: number,
      },
      clusterType: RedisClusterTypes,
      shardNum: number,
    };
    title?: string,
    showTitleTag?: boolean,
  }

  export interface CapacityNeed {
    current: number,
    future: number,
  }

  type FilterClusterSpecItem = ServiceReturnType<typeof getFilterClusterSpec>[0];

  interface Emits {
    (e: 'click-confirm', obj: FilterClusterSpecItem, capacity: CapacityNeed): void
    (e: 'click-cancel'): void
  }


  const props  = withDefaults(defineProps<Props>(), {
    isShow: false,
    isSameShardNum: false, // 集群容量变更才需要
    data: () => ({
      targetCluster: '',
      currentSepc: '',
      capacity: {
        total: 1,
        used: 0,
      },
      clusterType: RedisClusterTypes.TwemproxyRedisInstance,
      shardNum: 0,
    }),
    title: '',
    showTitleTag: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const capacityNeed = ref();
  const capacityFutureNeed = ref();
  const radioValue  = ref(-1);
  const radioChoosedId  = ref(''); // 标记，sort重新定位index用
  const isTableLoading = ref(false);
  const isConfirmLoading = ref(false);
  const tableData = ref<FilterClusterSpecItem[]>([]);
  const targetCapacity = ref({
    current: props.data?.capacity.total ?? 1,
    total: 1,
  });
  const targetSepc = ref('');

  const isShowGreaterTip = computed(() => capacityFutureNeed.value < capacityNeed.value);
  const isAbleSubmit = computed(() => radioValue.value !== -1);

  // const currentPercent = computed(() => {
  //   if (props?.data) {
  //     return Number(((props.data.capacity.used / props.data.capacity.total) * 100).toFixed(2));
  //   }
  //   return 0;
  // });

  // const currentSpec = computed(() => {
  //   if (props?.data) {
  //     return `(${props.data.capacity.used}G/${props.data.capacity.total}G)`;
  //   }
  //   return '(0G/0G)';
  // });

  const currentSpec = computed(() => {
    if (props?.data) {
      return `${props.data.capacity.total}G`;
    }
    return '(0G)';
  });

  // const targetPercent = computed(() => Number(((props.data.capacity.used
  //   / targetCapacity.value.total) * 100).toFixed(2)));

  const changeObj = computed(() => {
    const diff = targetCapacity.value.total - targetCapacity.value.current;
    const rate = ((diff / targetCapacity.value.current) * 100).toFixed(2);
    if (diff < 0) {
      return {
        rate,
        num: diff,
      };
    }
    return {
      rate: `+${rate}`,
      num: `+${diff}`,
    };
  });

  const isDataChange = computed(() => capacityNeed.value !== 0 || capacityFutureNeed.value !== 0
    || radioValue.value !== -1);

  const cluserMachineMap = {
    [RedisClusterTypes.PredixyTendisplusCluster]: 'tendisplus',
    [RedisClusterTypes.TwemproxyRedisInstance]: 'tendiscache',
    [RedisClusterTypes.TwemproxyTendisSSDInstance]: 'tendisssd',
  };

  const columns = computed(() => {
    const totalColums = [
      {
        label: t('资源规格'),
        field: 'spec',
        showOverflowTooltip: true,
        width: 260,
        render: ({ index, row }: { index: number, row: RedisClusterSpecModel }) => (
          <div style="display:flex;align-items:center;">
            <bk-radio label={index} v-model={radioValue.value}>{row.spec_name}</bk-radio>
          </div>
        ),
      },
      {
        label: t('需机器组数'),
        field: 'machine_pair',
        sort: true,
      },
      {
        label: t('集群分片'),
        field: 'cluster_shard_num',
        sort: true,
      },
      {
        label: t('集群容量(G)'),
        field: 'cluster_capacity',
        sort: true,
      },
    ];
    if (props.isSameShardNum) {
      // 集群容量变更，去除集群分片列
      totalColums.splice(2, 1);
    }
    return totalColums;
  });

  let rawTableData: FilterClusterSpecItem[] = [];

  watch(() => props.data, (data) => {
    if (data) {
      targetCapacity.value.current = data.capacity.total;
    }
  }, {
    immediate: true,
  });

  watch(capacityNeed, (data) => {
    if (data && data > 0 && data !== capacityFutureNeed.value) {
      capacityFutureNeed.value = data;
    }
  }, {
    immediate: true,
  });

  watch(radioValue, (index) => {
    if (index === -1) return;
    const plan = tableData.value[index];
    targetCapacity.value.total = plan.cluster_capacity;
    targetSepc.value = plan.spec_name;
  });

  const handleSearchClusterSpec = async () => {
    if (capacityNeed.value === undefined || capacityFutureNeed.value === undefined) {
      return;
    }
    if (capacityNeed.value > 0 && capacityFutureNeed.value > 0) {
      isTableLoading.value = true;
      const clusterType = props.data?.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance;
      const params = {
        spec_cluster_type: clusterType,
        spec_machine_type: cluserMachineMap[clusterType],
        shard_num: props.data.shardNum === 0 ? undefined : props.data.shardNum,
        capacity: capacityNeed.value,
        future_capacity: capacityNeed.value <= capacityFutureNeed.value ? capacityFutureNeed.value : capacityNeed.value,
      };
      if (!props.isSameShardNum) {
        delete params.shard_num;
      }
      const retArr = await getFilterClusterSpec(params).finally(() => {
        isTableLoading.value = false;
      });
      tableData.value = retArr;
      rawTableData = _.cloneDeep(retArr);
    }
  };

  // 点击确定
  const handleConfirm = () => {
    const index = radioValue.value;
    if (index === -1) {
      return;
    }
    emits('click-confirm', tableData.value[index], { current: capacityNeed.value, future: capacityFutureNeed.value });
  };

  async function handleClose() {
    const result = await handleBeforeClose(isDataChange.value);
    if (!result) return;
    window.changeConfirm = false;
    emits('click-cancel');
  }

  const handleRowClick = (event: PointerEvent, row: FilterClusterSpecItem, index: number) => {
    radioValue.value = index;
    radioChoosedId.value = row.spec_name;
  };

  const handleColumnSort = (data: { column: { field: string }, index: number, type: string }) => {
    const { column, type } = data;
    const filed = column.field as keyof FilterClusterSpecItem;
    if (type === 'asc') {
      tableData.value.sort((prevItem, nextItem) => prevItem[filed] as number - (nextItem[filed] as number));
    } else if (type === 'desc') {
      tableData.value.sort((prevItem, nextItem) => nextItem[filed] as number - (prevItem[filed] as number));
    } else {
      tableData.value = rawTableData;
    }
    const index = tableData.value.findIndex(item => item.spec_name === radioChoosedId.value);
    radioValue.value = index;
  };
</script>

<style lang="less" scoped>

.positive {
  color: #EA3636;
}

.negtive {
  color: #2DCB56;
}

.main-box {
  display: flex;
  width: 100%;
  padding: 24px 40px;
  flex-direction: column;

  .capacity-panel {
    width: 880px;
    padding: 16px;
    margin-bottom: 24px;
    background: #FAFBFD;

    .panel-row {
      display: flex;
      width: 100%;

      .column {
        display: flex;
        width: 50%;
        align-items: center;

        .title {
          height: 18px;
          font-size: 12px;
          line-height: 18px;
          letter-spacing: 0;
          color: #63656E;
          text-align: right;
        }

        .content {
          flex:1;
          display: flex;
          font-size: 12px;
          color: #63656E;

          .percent {
            margin-left: 4px;
            font-size: 12px;
            font-weight: bold;
            color: #313238;
          }

          .spec {
            margin-left: 2px;
            font-size: 12px;
            font-weight: bold;
            color: #63656E;
          }

          .scale-percent {
            margin-left: 5px;
            font-size: 12px;
            font-weight: bold;
          }
        }
      }
    }
  }

  .select-group {
    position: relative;
    display: flex;
    width: 880px;
    gap: 38px;

    .select-box {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;

      .input-box {
        display: flex;
        width: 100%;
        align-items: center;

        .num-input {
          height: 32px;
        }

        .uint {
          margin-left: 12px;
          font-size: 12px;
          color: #63656E;
        }
      }

      .gt-tip {
        position: absolute;
        right: 252px;
        bottom: -20px;

        span {
          font-size: 12px;
          color: #EA3636;
        }
      }
    }
  }

  .deploy-box {
    margin-top: 24px;

    .deploy-table {
      margin-top: 6px;

      :deep(.cluster-name) {
        padding: 8px 0;
        line-height: 16px;

        &__alias {
          color: @light-gray;
        }
      }

      :deep(.bk-form-label) {
        display: none;
      }

      :deep(.bk-form-error-tips) {
        top: 50%;
        transform: translateY(-50%);
      }

      :deep(.regex-input) {
        margin: 8px 0;
      }
    }
  }

  .spec-title {
    border-bottom: 1px dashed #979BA5;
  }

}


</style>
