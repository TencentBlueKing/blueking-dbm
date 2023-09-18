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
              v-model="capacityNeed"
              class="mb10 num-input"
              :min="0"
              size="small"
              type="number"
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
              v-model="capacityFutureNeed"
              class="mb10 num-input"
              :min="0"
              size="small"
              type="number"
              @change="(value) => capacityFutureNeed = Number(value)" />
            <div class="uint">
              G
            </div>
          </div>
          <div
            v-if="isShowGreaterTip"
            class="gt-tip">
            <span>{{ t('未来容量必须大于目标容量') }}</span>
          </div>
        </div>
      </div>
      <div class="qps-box">
        <div class="title-spot">
          {{ t('QPS 预估范围') }}<span class="required" />
        </div>
        <BkLoading :loading="isSliderLoading">
          <BkSlider
            v-model="qpsRange"
            :formatter-label="formatterLabel"
            :max-value="qpsSelectRange.max"
            :min-value="qpsSelectRange.min"
            range
            show-between-label
            show-input
            show-tip
            style="width: 800px;font-size: 12px;" />
        </BkLoading>
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
            @row-click.stop="handleRowClick">
            <template #empty>
              <p
                v-if="!qpsRange[1]"
                style="width: 100%; line-height: 128px; text-align: center;">
                <DbIcon
                  class="mr-4"
                  type="attention" />
                <span>{{ t('请先设置容量及QPS范围') }}</span>
              </p>
              <BkException
                v-else
                :description="t('无匹配的资源规格_请先修改容量及QPS设置')"
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
<script lang="tsx">
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
    showGreaterTip?: boolean,
  }
</script>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { RedisClusterTypes } from '@services/model/redis/redis';
  import RedisClusterSpecModel from '@services/model/resource-spec/redis-cluster-sepc';
  import { type FilterClusterSpecItem, getFilterClusterSpec, queryQPSRange } from '@services/resourceSpec';

  import { useBeforeClose } from '@hooks';

  import specTipImg from '@images/spec-tip.png';

  interface Emits {
    (e: 'click-confirm', obj: FilterClusterSpecItem): void
    (e: 'click-cancel'): void
  }

  const props  = withDefaults(defineProps<Props>(), {
    isShow: false,
    isSameShardNum: false,
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
    showGreaterTip: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const capacityNeed = ref(0);
  const capacityFutureNeed = ref(0);
  const radioValue  = ref(-1);
  const qpsSelectRange = ref({
    min: 0,
    max: 1,
  });
  const qpsRange = ref([0, 1]);
  const isSliderLoading = ref(false);
  const isTableLoading = ref(false);

  const timer = ref();
  const isConfirmLoading = ref(false);
  const tableData = ref<FilterClusterSpecItem[]>([]);
  const targetCapacity = ref({
    current: props.data?.capacity.total ?? 1,
    total: 1,
  });
  const targetSepc = ref('');
  const queryTimer = ref();

  const isShowGreaterTip = computed(() => props.showGreaterTip && capacityFutureNeed.value < capacityNeed.value);

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

  const columns = [
    {
      label: () => <bk-popover
        theme="light"
        class="tip-box"
        width="210"
        height="78"
        >
          {{
            default: () => <div style="border-bottom: 1px dashed #979BA5;">{t('资源规格')}</div>,
            content: () => <img style="width:182px;height:63px" src={specTipImg} />,
          }}
        </bk-popover>,
      field: 'spec',
      showOverflowTooltip: false,
      width: 260,
      render: ({ index, row }: { index: number, row: RedisClusterSpecModel }) => (
      <div style="display:flex;align-items:center;">
        <bk-radio label={index} v-model={radioValue.value}>{row.spec_name}</bk-radio>
        {/* <bk-tag theme={data.tip_type === 'recommand' ?
          'success' : data.tip_type === 'current_plan' ? 'info' : 'danger'} style="margin-left:5px">
          {data.tip_type}
        </bk-tag> */}
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
    {
      label: t('集群QPS(每秒)'),
      field: 'qps',
      sort: {
        sortFn: (a: RedisClusterSpecModel, b: RedisClusterSpecModel, type: 'asc' | 'desc') => handleSortQPS(a, b, type),
      },
      render: ({ row }: { row: RedisClusterSpecModel }) => <div>{row.cluster_qps}/s</div>,
    },
  ];

  watch(() => props.isShow, () => {
    resetInfo();
  }, {
    immediate: true,
  });

  watch(() => [capacityNeed.value, capacityFutureNeed.value], (data) => {
    const [capacityNeed, capacityFutureNeed] = data;
    if (capacityNeed > 0 && capacityFutureNeed > 0) {
      isSliderLoading.value = true;
      clearTimeout(timer.value);
      timer.value = setTimeout(() => {
        queryLatestQPS();
      }, 1000);
    }
  });

  watch(radioValue, (index) => {
    if (index === -1) return;
    const plan = tableData.value[index];
    targetCapacity.value.total = plan.cluster_capacity;
    targetSepc.value = plan.spec_name;
  });

  watch(qpsRange, (data) => {
    clearTimeout(queryTimer.value);
    queryTimer.value = setTimeout(() => {
      handleSliderChange(data as [number, number]);
    }, 1000);
  });

  watch(qpsRange, (data) => {
    clearTimeout(queryTimer.value);
    queryTimer.value = setTimeout(() => {
      handleSliderChange(data as [number, number]);
    }, 1000);
  });

  const formatterLabel = (value: string) => `${value}/s`;

  // Slider变动
  const handleSliderChange = async (data: [number, number]) => {
    isTableLoading.value = true;
    qpsRange.value = data;
    const clusterType = props.data?.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance;
    const params = {
      spec_cluster_type: clusterType,
      spec_machine_type: cluserMachineMap[clusterType],
      shard_num: props.data.shardNum === 0 ? undefined : props.data.shardNum,
      capacity: capacityNeed.value,
      future_capacity: capacityNeed.value <= capacityFutureNeed.value ? capacityFutureNeed.value : capacityNeed.value,
      qps: {
        min: data[0],
        max: data[1],
      },
    };
    if (!props.isSameShardNum) {
      delete params.shard_num;
    }
    const retArr = await getFilterClusterSpec(params).finally(() => {
      isTableLoading.value = false;
    });
    tableData.value = retArr;
  };

  const handleSortQPS = (a: RedisClusterSpecModel, b: RedisClusterSpecModel, type: 'asc' | 'desc') => {
    if (type === 'asc') {
      return a.cluster_qps - b.cluster_qps;
    }
    return b.cluster_qps - a.cluster_qps;
  };

  // 点击确定
  const handleConfirm = () => {
    const index = radioValue.value;
    if (index === -1) {
      return;
    }
    emits('click-confirm', tableData.value[index]);
  };

  async function handleClose() {
    const result = await handleBeforeClose(isDataChange.value);
    if (!result) return;
    resetInfo();
    window.changeConfirm = false;
    emits('click-cancel');
  }

  // 查询最新的QPS
  const queryLatestQPS = async () => {
    const clusterType = props.data?.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance;
    const ret = await queryQPSRange({
      spec_cluster_type: clusterType,
      spec_machine_type: cluserMachineMap[clusterType],
      capacity: capacityNeed.value,
      future_capacity: capacityNeed.value <= capacityFutureNeed.value ? capacityFutureNeed.value : capacityNeed.value,
    }).finally(() => {
      isSliderLoading.value = false;
    });
    const { min, max } = ret;
    qpsSelectRange.value = {
      min,
      max: max === 0 ? 10 : max,
    };
    qpsRange.value = [min, max];
  };

  const handleRowClick = (event: PointerEvent, row: FilterClusterSpecItem, index: number) => {
    radioValue.value = index;
  };

  function resetInfo() {
    capacityNeed.value = 0;
    capacityFutureNeed.value = 0;
    targetSepc.value = '';
    targetCapacity.value = {
      current: props.data?.capacity.total ?? 1,
      total: 1,
    };
    radioValue.value = -1;
    qpsSelectRange.value = {
      min: 0,
      max: 1,
    };
    qpsRange.value = [0, 1];
    tableData.value = [];
  }
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
    height: 78px;
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
            color: #979BA5;
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
    margin-bottom: 24px;
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
        right: 275px;
        bottom: -20px;

        span {
          font-size: 12px;
          color: #EA3636;
        }
      }
    }
  }

  .qps-box {
    display: flex;
    width: 100%;
    margin-bottom: 12px;
    flex-direction: column;
    gap: 10px;
  }

  .deploy-box {
    margin-top: 34px;

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
