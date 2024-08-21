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
          <div class="row-column row-column-left">
            <div
              class="column-title"
              style="min-width: 70px">
              {{ t('当前总容量') }}：
            </div>
            <div class="column-content">
              <ClusterCapacityUsageRate :cluster-stats="clusterStats" />
            </div>
          </div>
          <div class="row-column row-column-right">
            <div
              class="column-title"
              style="min-width: 82px">
              {{ t('目标容量') }}：
            </div>
            <div class="column-content">
              <template v-if="targetInfo.spec.name">
                <ClusterCapacityUsageRate :cluster-stats="targetClusterStats" />
                <ValueDiff
                  :current-value="currentCapacity"
                  num-unit="G"
                  :target-value="targetInfo.capacity" />
              </template>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('请先选择部署方案') }}
              </span>
            </div>
          </div>
        </div>
        <div class="panel-row mt-4">
          <div class="row-column row-column-left">
            <div class="column-title">{{ t('当前资源规格') }}：</div>
            <div class="column-content">
              <RenderSpec
                :data="data.currentSepc"
                :hide-qps="!data.currentSepc.qps.max"
                is-ignore-counts />
            </div>
          </div>
          <div class="row-column row-column-right">
            <div class="column-title">{{ t('目标资源规格') }}：</div>
            <div class="column-content">
              <span v-if="targetInfo.spec.name">
                <RenderSpec
                  :data="targetInfo.spec"
                  :hide-qps="!targetInfo.spec.qps.max"
                  is-ignore-counts />
              </span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('--') }}
              </span>
            </div>
          </div>
        </div>
        <div class="panel-row mt-4">
          <div class="row-column row-column-left">
            <div class="column-title">{{ t('当前机器组数') }}：</div>
            <div class="column-content">
              <span class="number-style">{{ data?.groupNum }}</span>
            </div>
          </div>
          <div class="row-column row-column-right">
            <div class="column-title">{{ t('目标机器组数') }}：</div>
            <div class="column-content">
              <span v-if="targetInfo.spec.name">
                <span class="number-style">{{ targetInfo.groupNum }}</span>
                <ValueDiff
                  :current-value="data.groupNum"
                  :show-rate="false"
                  :target-value="targetInfo.groupNum" />
              </span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('--') }}
              </span>
            </div>
          </div>
        </div>
        <div class="panel-row panel-row mt-4">
          <div class="row-column row-column-left">
            <div class="column-title">{{ t('当前机器数量') }}：</div>
            <div class="column-content">
              <span class="number-style">{{ data?.groupNum * 2 }}</span>
            </div>
          </div>
          <div class="row-column row-column-right">
            <div class="column-title">{{ t('目标机器数量') }}：</div>
            <div class="column-content">
              <span v-if="targetInfo.spec.name">
                <span class="number-style">{{ targetInfo.groupNum * 2 }}</span>
                <ValueDiff
                  :current-value="data.groupNum * 2"
                  :show-rate="false"
                  :target-value="targetInfo.groupNum * 2" />
              </span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('--') }}
              </span>
            </div>
          </div>
        </div>
        <div class="panel-row panel-row mt-4">
          <div class="row-column row-column-left">
            <div class="column-title">{{ t('当前分片数') }}：</div>
            <div class="column-content">
              <span class="number-style">{{ data?.shardNum }}</span>
            </div>
          </div>
          <div class="row-column row-column-right">
            <div class="column-title">{{ t('目标分片数') }}：</div>
            <div class="column-content">
              <span v-if="targetInfo.spec.name">
                <span class="number-style">{{ targetInfo.shardNum }}</span>
                <ValueDiff
                  :current-value="data.shardNum"
                  :show-rate="false"
                  :target-value="targetInfo.shardNum" />
              </span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('--') }}
              </span>
            </div>
          </div>
        </div>
        <div class="panel-row panel-row mt-4">
          <div class="row-column row-column-left"></div>
          <div class="row-column row-column-right">
            <div class="column-title">{{ t('变更方式') }}：</div>
            <div class="column-content">
              <span v-if="targetInfo.spec.name">{{
                targetInfo.updateMode === 'keep_current_machines' ? t('原地变更') : t('替换变更')
              }}</span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('--') }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div class="deploy-box">
        <div class="title-spot">{{ t('集群部署方案') }}<span class="required" /></div>
        <div class="input-box">
          <BkInput
            ref="capacityInputRef"
            class="mb10"
            :min="0"
            :model-value="capacityNeed"
            :prefix="t('目标容量')"
            style="width: 450px"
            suffix="G"
            type="number"
            @blur="handleSearchClusterSpec"
            @change="(value) => (capacityNeed = Number(value))"
            @enter="handleCapacityNeedEnter" />
          <div class="uint-text ml-12">
            <span>{{ t('当前') }}</span>
            <span class="spec-text">{{ props.data.capacity.total ?? 0 }}</span>
            <span>G</span>
          </div>
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
                v-if="!capacityNeed"
                style="width: 100%; line-height: 128px; text-align: center">
                <DbIcon
                  class="mr-4"
                  type="attention" />
                <span>{{ t('请先设置容量') }}</span>
              </p>
              <BkException
                v-else
                :description="t('无匹配的资源规格_请先修改容量设置')"
                scene="part"
                style="font-size: 12px"
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
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RedisModel, { RedisClusterTypes } from '@services/model/redis/redis';
  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';
  import { getRedisClusterCapacityUpdateInfo } from '@services/source/redisToolbox'

  import { useBeforeClose } from '@hooks';

  import ClusterCapacityUsageRate from '@components/cluster-capacity-usage-rate/Index.vue'
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue'

  import { convertStorageUnits, messageError } from '@utils';

  export interface CapacityNeed {
    current: number,
    future: number,
  }

  export interface TargetInfo {
    capacity: number,
    spec: {
      name: string,
      cpu: ClusterSpecModel['cpu'],
      id: number,
      mem: ClusterSpecModel['mem'],
      qps: ClusterSpecModel['qps'],
      storage_spec: ClusterSpecModel['storage_spec']
    },
    groupNum: number,
    requireMachineGroupNum: number,
    shardNum: number,
    updateMode: string
  }

  export interface Props {
    isShow?: boolean;
    isSameShardNum?: boolean;
    data?: {
      targetCluster: string,
      currentSepc: TargetInfo['spec']
      capacity: {
        total: number,
        used: number,
      },
      clusterType: RedisClusterTypes,
      groupNum: number,
      shardNum: number,
    };
    title?: string,
    showTitleTag?: boolean,
    targetVerison?: string
    clusterId?: number,
    clusterStats: RedisModel['cluster_stats'],
    targetObject?: UnwrapRef<typeof targetInfo>
  }

  interface Emits {
    (e: 'clickConfirm', obj: ClusterSpecModel, capacity: number, target: UnwrapRef<typeof targetInfo>): void
    (e: 'clickCancel'): void
    (e: 'targetStatsChange', value: RedisModel['cluster_stats']): void
  }

  const props  = withDefaults(defineProps<Props>(), {
    isShow: false,
    isSameShardNum: false, // 集群容量变更才需要
    data: () => ({
      targetCluster: '',
      currentSepc: {
        name: '',
        cpu: {} as ClusterSpecModel['cpu'],
        id: 0,
        mem: {} as ClusterSpecModel['mem'],
        qps: {} as ClusterSpecModel['qps'],
        storage_spec: [] as ClusterSpecModel['storage_spec']
      },
      capacity: {
        total: 1,
        used: 0,
      },
      clusterType: RedisClusterTypes.TwemproxyRedisInstance,
      groupNum: 0,
      requireMachineGroupNum: 0,
      shardNum: 0,
    }),
    title: '',
    showTitleTag: true,
    targetVerison: undefined,
    clusterId: undefined,
    targetObject: undefined
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const createDefaultTargetInfo = () => ({
    capacity: 0,
    spec: {
      name: '',
      cpu: {} as ClusterSpecModel['cpu'],
      id: 0,
      mem: {} as ClusterSpecModel['mem'],
      qps: {} as ClusterSpecModel['qps'],
      storage_spec: [] as ClusterSpecModel['storage_spec']
    },
    groupNum: 0,
    requireMachineGroupNum: 0,
    shardNum: 0,
    updateMode: ''
  })

  const capacityInputRef = ref()
  const capacityNeed = ref();
  const radioValue = ref(-1);
  const radioChoosedId  = ref(''); // 标记，sort重新定位index用
  const isTableLoading = ref(false);
  const isConfirmLoading = ref(false);
  const tableData = ref<ClusterSpecModel[]>([]);
  const targetInfo = ref(createDefaultTargetInfo());

  const specDisabledMap = shallowRef<Record<number, boolean>>({})

  const isAbleSubmit = computed(() => radioValue.value !== -1);

  const isDataChange = computed(() => capacityNeed.value !== undefined
    || radioValue.value !== -1);

  const targetClusterStats = computed(() => {
    let stats = {} as RedisModel['cluster_stats']
    if (!_.isEmpty(props.clusterStats)) {
      const { used } = props.clusterStats;
      const targetTotal = convertStorageUnits(targetInfo.value.capacity, 'GB', 'B')

      stats = {
        used,
        total: targetTotal,
        in_use: Number((used / targetTotal * 100).toFixed(2))
      }
    }

    emits('targetStatsChange', stats)
    return stats
  })

  const currentCapacity = computed(() => {
    if (_.isEmpty(props.clusterStats)) {
      return props.data.capacity.total ?? 0
    }
    return convertStorageUnits(props.clusterStats.total, 'B', 'GB')
  })

  const cluserMachineMap = {
    [RedisClusterTypes.PredixyTendisplusCluster]: 'tendisplus',
    [RedisClusterTypes.PredixyRedisCluster]: 'tendiscache',
    [RedisClusterTypes.RedisInstance]: 'tendiscache',
    [RedisClusterTypes.TwemproxyRedisInstance]: 'tendiscache',
    [RedisClusterTypes.TwemproxyTendisSSDInstance]: 'tendisssd',
  };

  const columns =  [
    {
      label: t('资源规格'),
      field: 'spec',
      showOverflowTooltip: true,
      width: 260,
      render: ({ index, row }: { index: number, row: ClusterSpecModel }) => (
        <div style="display:flex;align-items:center;">
          <bk-radio
            label={index}
            v-model={radioValue.value}
            disabled={specDisabledMap.value[row.spec_id]}>
            <span style="font-size: 12px">{row.spec_name}</span>
          </bk-radio>
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

  let rawTableData: ClusterSpecModel[] = [];

  watch(() => props.isShow, () => {
    if (props.isShow) {
      capacityNeed.value = ''
      radioValue.value = -1
      tableData.value = [];
      rawTableData = []
      specDisabledMap.value = {}
      targetInfo.value = props.targetObject || createDefaultTargetInfo()
    }
  })

  watch(radioValue, () => {
    if (radioValue.value !== -1) {
      getUpdateInfo(tableData.value[radioValue.value])
    }
  })

  const handleSearchClusterSpec = async () => {
    if (capacityNeed.value === undefined) {
      return;
    }
    if (capacityNeed.value > 0) {
      isTableLoading.value = true;
      const clusterType = props.data?.clusterType ?? RedisClusterTypes.TwemproxyRedisInstance;
      const params = {
        spec_cluster_type: clusterType,
        spec_machine_type: cluserMachineMap[clusterType],
        shard_num: props.data.shardNum === 0 ? undefined : props.data.shardNum,
        capacity: capacityNeed.value,
        future_capacity: capacityNeed.value,
      };
      if (!props.isSameShardNum) {
        delete params.shard_num;
      }
      const retArr = await getFilterClusterSpec(params).finally(() => {
        isTableLoading.value = false;
      });
      radioValue.value = -1
      targetInfo.value = createDefaultTargetInfo()
      tableData.value = retArr;
      rawTableData = _.cloneDeep(retArr);
      specDisabledMap.value = {}
    }
  };

  const handleCapacityNeedEnter = () => {
    capacityInputRef.value.blur()
  }

  // 点击确定
  const handleConfirm = () => {
    const index = radioValue.value;
    if (index === -1) {
      return;
    }
    emits('clickConfirm', tableData.value[index], capacityNeed.value, targetInfo.value);
  };

  async function handleClose() {
    const result = await handleBeforeClose(isDataChange.value);
    if (!result) return;
    window.changeConfirm = false;
    emits('clickCancel');
  }

  const getUpdateInfo = (row: ClusterSpecModel) => {
    getRedisClusterCapacityUpdateInfo({
      cluster_id: props.clusterId!,
      new_storage_version: props.targetVerison!,
      new_spec_id : row.spec_id,
      new_machine_group_num: row.machine_pair,
      new_shards_num: row.cluster_shard_num
    }).then((updateInfo) => {
      if (updateInfo.err_msg) {
        messageError(updateInfo.err_msg)
        radioValue.value = -1;
        radioChoosedId.value = '';
        specDisabledMap.value[row.spec_id] = true
        return
      }
      targetInfo.value = {
        capacity: row.cluster_capacity,
        spec: {
          name: row.spec_name,
          cpu: row.cpu,
          id: row.spec_id,
          mem: row.mem,
          qps: row.qps,
          storage_spec: row.storage_spec
        },
        groupNum: row.machine_pair,
        requireMachineGroupNum: updateInfo.require_machine_group_num,
        shardNum: row.cluster_shard_num,
        updateMode: updateInfo.capacity_update_type
      }
      radioChoosedId.value = row.spec_name;
    })
  }

  const handleRowClick = (event: PointerEvent, row: ClusterSpecModel, index: number) => {
    if (index === radioValue.value || specDisabledMap.value[row.spec_id]) {
      return
    }

    radioValue.value = index
  };

  const handleColumnSort = (data: { column: { field: string }, index: number, type: string }) => {
    const { column, type } = data;
    const filed = column.field as keyof ClusterSpecModel;
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
  .main-box {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

    .capacity-panel {
      width: 880px;
      padding: 16px;
      background: #fafbfd;

      .panel-row {
        display: flex;
        width: 100%;

        .row-column-left {
          width: 40%;
        }

        .row-column-right {
          width: 60%;
        }

        .row-column {
          display: flex;
          align-items: center;

          .column-title {
            width: 100px;
            height: 18px;
            font-size: 12px;
            line-height: 18px;
            letter-spacing: 0;
            color: #63656e;
            text-align: right;
          }

          .column-content {
            flex: 1;
            display: flex;
            font-size: 12px;
            color: #63656e;

            :deep(.render-spec-box) {
              height: 100%;
              padding: 0;
              line-height: 22px;
            }

            .number-style {
              margin-left: 2px;
              font-size: 12px;
              font-weight: bold;
              color: #313238;
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

          // .uint {
          //   margin-left: 12px;
          //   font-size: 12px;
          //   color: #63656e;
          // }
        }

        .gt-tip {
          position: absolute;
          right: 252px;
          bottom: -20px;

          span {
            font-size: 12px;
            color: #ea3636;
          }
        }
      }
    }

    .deploy-box {
      margin-top: 24px;

      .input-box {
        display: flex;
        align-items: center;
        margin-top: 12px;

        .uint-text {
          font-size: 12px;

          .spec-text {
            margin: 0 2px;
            font-weight: 700;
          }
        }
      }

      .deploy-table {
        margin-top: 12px;

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
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
