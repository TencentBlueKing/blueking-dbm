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
    :before-close="handleBeforeClose"
    :is-show="isShow"
    :width="960"
    @closed="handleClose">
    <template #header>
      <span>
        {{ $t('选择集群目标方案') }}
        【{{ data?.targetCluster }}】
        <BkTag theme="info">
          存储层
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="capacity-panel">
        <div class="panel-row">
          <div class="column">
            <div class="title">
              当资源规格：
            </div>
            <div class="content">
              {{ data?.currentSepc }}
            </div>
          </div>
          <div class="column">
            <div class="title">
              变更后的规格：
            </div>
            <div class="content">
              {{ targetSepc }}
            </div>
          </div>
        </div>
        <div
          class="panel-row"
          style="margin-top: 12px;">
          <div class="column">
            <div class="title">
              当前容量：
            </div>
            <div class="content">
              <BkProgress
                color="#EA3636"
                :percent="35"
                :show-text="false"
                size="small"
                :stroke-width="16"
                type="circle"
                :width="15" />
              <span class="percent">{{ currentPercent }}%</span>
              <span class="spec">{{ currentSpec }}</span>
            </div>
          </div>
          <div class="column">
            <div class="title">
              变更后容量：
            </div>
            <div class="content">
              <BkProgress
                color="#2DCB56"
                :percent="targetPercent"
                :show-text="false"
                size="small"
                :stroke-width="16"
                type="circle"
                :width="15" />
              <span class="percent">{{ targetPercent }}%</span>
              <span class="spec">{{ `(${targetCapacity.used}G/${targetCapacity.total}G)` }}</span>
              <span
                class="scale-percent"
                :style="{color: targetCapacity.total > targetCapacity.current ?
                  '#EA3636' : '#2DCB56'}">{{ `(${changeObj.rate}%, ${changeObj.num}G)` }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="select-group">
        <div class="select-box">
          <div class="title-spot">
            目标集群容量需求<span class="edit-required" />
          </div>
          <div class="input-box">
            <BkInput
              v-model="capacityNeed"
              class="mb10"
              clearable
              :max="100"
              :min="1"
              size="small"
              type="number" />
            <div class="uint">
              G
            </div>
          </div>
        </div>
        <div class="select-box">
          <div class="title-spot">
            未来集群容量需求<span class="edit-required" />
          </div>
          <div class="input-box">
            <BkInput
              v-model="capacityFutureNeed"
              class="mb10"
              clearable
              :max="100000000"
              :min="1"
              size="small"
              type="number" />
            <div class="uint">
              G
            </div>
          </div>
        </div>
      </div>
      <div class="qps-box">
        <div class="title-spot">
          QPS 预估范围<span class="edit-required" />
        </div>
        <BkSlider
          v-model="qpsRange"
          :formatter-label="formatterLabel"
          :max-value="qpsSelectRange.max"
          :min-value="qpsSelectRange.min"
          range
          show-interval
          show-interval-label
          :step="qpsRangeStep"
          @change="handleSliderChange" />
      </div>
      <div class="deploy-box">
        <div class="title-spot">
          集群部署方案<span class="edit-required" />
        </div>
        <DbOriginalTable
          class="deploy-table"
          :columns="columns"
          :data="tableData" />
      </div>
    </div>

    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isConfirmLoading"
        theme="primary"
        @click="handleConfirm">
        {{ $t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isConfirmLoading"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { RedisClusterTypes } from '@services/model/redis/redis';
  import RedisClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getFilterClusterSpec, queryQPSRange } from '@services/resourceSpec';

  import { useBeforeClose } from '@hooks';

  import specTipImg from '@images/spec-tip.png';

  import type { IDataRow } from './Row.vue';


  interface Props {
    data?: IDataRow;
  }

  interface Emits {
    (e: 'on-confirm', obj: RedisClusterSpecModel): void
  }

  const props  = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const capacityNeed = ref(0);
  const capacityFutureNeed = ref(0);
  const radioValue  = ref(-1);
  const qpsSelectRange = ref({
    min: 0,
    max: 1000,
  });
  const qpsRange = ref([0, 0]);
  const timer = ref();
  const isConfirmLoading = ref(false);
  const tableData = ref<RedisClusterSpecModel[]>([]);
  const targetCapacity = ref({
    current: props.data?.currentCapacity?.total ?? 1,
    used: props.data?.currentCapacity?.used ?? 1,
    total: 1,
  });
  const targetSepc = ref('0核0GB_0GB_QPS:0');

  const qpsRangeStep = computed(() => Math.floor((qpsSelectRange.value.max - qpsSelectRange.value.min) / 10));

  const currentPercent = computed(() => {
    if (props.data && props.data.currentCapacity) {
      return Number(((props.data.currentCapacity.used / props.data.currentCapacity.total) * 100).toFixed(2));
    }
    return 0;
  });

  const currentSpec = computed(() => {
    if (props?.data && props.data?.currentCapacity) {
      return `(${props.data.currentCapacity.used}G/${props.data.currentCapacity.total}G)`;
    }
    return '(0G/0G)';
  });

  const targetPercent = computed(() => Number(((targetCapacity.value.used
    / targetCapacity.value.total) * 100).toFixed(2)));

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
      render: ({ index, data }: { index: number, data: RedisClusterSpecModel }) => (
      <div style="display:flex;align-items:center;">
        <bk-radio label={index} v-model={radioValue.value}>{data.spec_name}</bk-radio>
        {/* <bk-tag theme={data.tip_type === 'recommand' ?
          'success' : data.tip_type === 'current_plan' ? 'info' : 'danger'} style="margin-left:5px">
          {data.tip_type}
        </bk-tag> */}
      </div>
    ),
    }, {
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
      sort: true,
      render: ({ data }: { data: RedisClusterSpecModel }) => <div>{data.qps.max}/s</div>,
    }];

  watch(() => [capacityNeed.value, capacityFutureNeed.value], (data) => {
    const [capacityNeed, capacityFutureNeed] = data;
    if (capacityNeed > 0 && capacityFutureNeed > 0) {
      clearTimeout(timer.value);
      timer.value = setTimeout(() => {
        queryLatestQPS();
      }, 1000);
    }
  });

  watch(radioValue, (index) => {
    const plan = tableData.value[index];
    targetCapacity.value.total = plan.cluster_capacity;
    targetSepc.value = `${plan.cpu.max}核${plan.mem.max}GB_${plan.cluster_capacity}GB_QPS:${plan.qps.max}`;
  });

  const formatterLabel = (value: string) => <span>{value}/s</span>;

  // Slider变动
  const handleSliderChange = async (data: [number, number]) => {
    qpsRange.value = data;
    const clusterType = props.data?.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance;
    const retArr = await getFilterClusterSpec({
      spec_cluster_type: clusterType,
      spec_machine_type: cluserMachineMap[clusterType],
      capacity: Number(capacityNeed.value),
      future_capacity: Number(capacityFutureNeed.value),
      qps: {
        min: data[0],
        max: data[1],
      },
    });
    tableData.value = retArr;
  };

  // 点击确定
  const handleConfirm = () => {
    const index = radioValue.value;
    emits('on-confirm', tableData.value[index]);
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
  }

  // 查询最新的QPS
  const queryLatestQPS = async () => {
    const clusterType = props.data?.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance;
    const ret = await queryQPSRange({
      spec_cluster_type: clusterType,
      spec_machine_type: cluserMachineMap[clusterType],
      capacity: capacityNeed.value,
      future_capacity: capacityFutureNeed.value,
    });
    const { min, max } = ret;
    qpsSelectRange.value = {
      min,
      max: max === 0 ? 10 : max,
    };
  };
</script>

<style lang="less" scoped>
.title-spot {
  position: relative;
  width: 100%;
  height: 20px;
  font-size: 12px;
  font-weight: 700;
  color: #63656E;

  .edit-required {
    position: relative;

    &::after {
      position: absolute;
      top: -10px;
      margin-left: 4px;
      font-size: 12px;
      line-height: 40px;
      color: #ea3636;
      content: "*";
    }
  }
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

        .title {
          width: 84px;
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
            color: #EA3636;
          }
        }
      }
    }
  }

  .select-group {
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

        .uint {
          margin-left: 12px;
          font-size: 12px;
          color: #63656E;
        }
      }
    }
  }

  .qps-box {
    display: flex;
    width: 100%;
    margin-bottom: 32px;
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
