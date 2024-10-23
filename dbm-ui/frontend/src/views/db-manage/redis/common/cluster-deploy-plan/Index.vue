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
    render-directive="if"
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
            <div class="title">{{ t('当前资源规格') }}：</div>
            <div class="content">
              {{ data?.currentSepc }}
            </div>
          </div>
          <div class="column">
            <div class="title">{{ t('变更后的规格') }}：</div>
            <div class="content">
              <span v-if="targetSepc">{{ targetSepc }}</span>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('请先选择部署方案') }}
              </span>
            </div>
          </div>
        </div>
        <div
          class="panel-row"
          style="margin-top: 12px">
          <div class="column">
            <div
              class="title"
              style="min-width: 70px">
              {{ t('当前总容量') }}：
            </div>
            <div class="content">
              <span class="spec">{{ currentSpec }}</span>
            </div>
          </div>
          <div class="column">
            <div
              class="title"
              style="min-width: 82px">
              {{ t('变更后总容量') }}：
            </div>
            <div class="content">
              <template v-if="targetSepc">
                <span class="spec">{{ `${targetCapacity.total}G` }}</span>
                <span
                  class="scale-percent"
                  :class="[targetCapacity.total > targetCapacity.current ? 'positive' : 'negtive']">
                  {{ `(${changeObj.num}G)` }}
                </span>
              </template>
              <span
                v-else
                style="color: #c4c6cc">
                {{ t('请先选择部署方案') }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div class="title-spot mb-8">{{ t('集群部署方案') }}<span class="required" /></div>
      <DbForm
        ref="formRef"
        class="plan-form"
        :label-width="200"
        :model="specInfo">
        <ApplySchema v-model="applySchema" />
        <template v-if="applySchema === APPLY_SCHEME.AUTO">
          <DbFormItem
            :label="targetCapacityTitle"
            required>
            <div class="input-box">
              <BkInput
                class="mb10 num-input"
                :min="0"
                :model-value="specInfo.capacityNeed"
                type="number"
                @blur="handleSearchClusterSpec"
                @change="(value) => (specInfo.capacityNeed = Number(value))" />
              <div class="uint">G</div>
            </div>
          </DbFormItem>
          <DbFormItem
            :label="futureCapacityTitle"
            required
            :rule="futrueCapacityRule">
            <div class="input-box">
              <BkInput
                class="mb10 num-input"
                :min="0"
                :model-value="specInfo.capacityFutureNeed"
                type="number"
                @blur="handleSearchClusterSpec"
                @change="(value) => (specInfo.capacityFutureNeed = Number(value))" />
              <div class="uint">G</div>
            </div>
          </DbFormItem>
          <div class="deploy-box">
            <BkLoading :loading="isTableLoading">
              <DbOriginalTable
                class="deploy-table"
                :columns="columns"
                :data="tableData"
                @column-sort="handleColumnSort"
                @row-click.stop="handleRowClick">
                <template #empty>
                  <p
                    v-if="!specInfo.capacityNeed || !specInfo.capacityFutureNeed"
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
        </template>
        <CustomSchema
          v-else
          ref="customSchemaRef"
          v-model="specInfo"
          :cluster-info="clusterInfo" />
      </DbForm>
    </div>
    <template #footer>
      <BkButton
        class="w-88 ml-16"
        :disabled="!isAbleSubmit"
        :loading="isConfirmLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
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

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { useBeforeClose } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue'

  import ApplySchema, { APPLY_SCHEME } from '@views/db-manage/common/apply-schema/Index.vue';
  import { ClusterMachineMap } from '@views/db-manage/redis/common/const'

  import CustomSchema from './CustomSchema.vue';

  export interface Props {
    isShow?: boolean;
    isSameShardNum?: boolean;
    data?: {
      targetCluster: string,
      currentSepcId: string,
      currentSepc: string,
      capacity: {
        total: number,
        used: number,
      },
      clusterType: ClusterTypes,
      shardNum: number,
      groupNum: number,
      bkCloudId: number
    };
    title?: string,
    showTitleTag?: boolean,
    hideShardColumn?: boolean;
  }

  export interface CapacityNeed {
    current: number,
    future: number,
  }

  export interface SpecResultInfo {
    cluster_capacity: number,
    max: number,
    cluster_shard_num: number,
    spec_id: number,
    machine_pair: number
  }

  type FilterClusterSpecItem = ServiceReturnType<typeof getFilterClusterSpec>[0];

  interface Emits {
    (e: 'click-confirm', obj: SpecResultInfo, capacity: CapacityNeed): void
    (e: 'click-cancel'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    isSameShardNum: false, // 集群容量变更才需要
    data: () => ({
      targetCluster: '',
      currentSepc: '',
      currentSepcId: '',
      capacity: {
        total: 1,
        used: 0,
      },
      clusterType: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      shardNum: 0,
      groupNum: 0,
      bkCloudId: 0
    }),
    title: '',
    showTitleTag: true,
    hideShardColumn: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const formRef = ref<InstanceType<typeof DbForm>>()
  const customSchemaRef = ref<InstanceType<typeof CustomSchema>>()
  const radioValue = ref(-1);
  const radioChoosedId  = ref(''); // 标记，sort重新定位index用
  const isTableLoading = ref(false);
  const isConfirmLoading = ref(false);
  const tableData = ref<FilterClusterSpecItem[]>([]);
  const targetCapacity = ref({
    current: props.data?.capacity.total ?? 1,
    total: 1,
  });
  const targetSepc = ref('');
  const applySchema = ref(APPLY_SCHEME.AUTO);

  const specInfo = reactive({
    capacityNeed: '' as number | '',
    capacityFutureNeed: '' as number | '',
    specId: '',
    count: 1,
    shardNum: 1,
    clusterShardNum: 1,
    totalCapcity: 0,
  })

  const clusterInfo = reactive({
    bizId: 0,
    cloudId: 0,
    clusterType: '',
    machineType: ''
  })

  const futrueCapacityRule = [
    {
      validator: (value: number) => value < Number(specInfo.capacityNeed || 0),
      trigger: 'change',
      message: t('未来容量必须大于等于目标容量'),
    },
  ]

  const isAbleSubmit = computed(() => {
    if (applySchema.value === APPLY_SCHEME.AUTO) {
      return radioValue.value !== -1
    }
    return true
  });
  const isTendisCache = computed(() => props.data.clusterType === ClusterTypes.TWEMPROXY_REDIS_INSTANCE);
  const targetCapacityTitle = computed(() => (isTendisCache.value ? t('目标集群容量需求(内存容量)') : t('目标集群容量需求(磁盘容量)')));
  const futureCapacityTitle = computed(() => (isTendisCache.value ? t('未来集群容量需求(内存容量)') : t('未来集群容量需求(磁盘容量)')));

  const currentSpec = computed(() => {
    if (props?.data) {
      return `${props.data.capacity.total}G`;
    }
    return '(0G)';
  });

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

  const isDataChange = computed(() => specInfo.capacityNeed !== '' || specInfo.capacityFutureNeed !== ''
    || radioValue.value !== -1);

  const columns = computed(() => {
    const totalColums = [
      {
        label: t('资源规格'),
        field: 'spec',
        showOverflowTooltip: true,
        width: 260,
        render: ({ index, row }: { index: number, row: ClusterSpecModel }) => (
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
    if (props.hideShardColumn) {
      // 集群容量变更，去除集群分片列
      totalColums.splice(2, 1);
    }
    return totalColums;
  });

  let rawTableData: FilterClusterSpecItem[] = [];

  watch(() => props.data, () => {
    if (props.data) {
      targetCapacity.value.current = props.data.capacity.total;
      Object.assign(specInfo, {
        count: props.data.groupNum,
        shardNum: props.data.shardNum / props.data.groupNum,
        clusterShardNum: props.data.shardNum,
      })
      Object.assign(clusterInfo, {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        cloudId: props.data.bkCloudId,
        clusterType: props.data.clusterType,
        machineType: ClusterMachineMap[props.data.clusterType]
      })
    }
  }, {
    immediate: true,
  });

  watch(() => specInfo.capacityNeed, (data) => {
    if (data && data > 0 && data !== specInfo.capacityFutureNeed) {
      specInfo.capacityFutureNeed = data;
    }
  }, {
    immediate: true,
  });

  watch(radioValue, (index) => {
    if (index === -1) {
      return;
    }
    const plan = tableData.value[index];
    targetCapacity.value.total = plan.cluster_capacity;
    targetSepc.value = plan.spec_name;
  });

  watch([() => specInfo.specId, () => specInfo.totalCapcity], () => {
    nextTick(() => {
      if (applySchema.value !== APPLY_SCHEME.AUTO) {
        targetCapacity.value.total = specInfo.totalCapcity;
        targetSepc.value = customSchemaRef.value!.getInfo().spec_name
      }
    })
  })

  const handleSearchClusterSpec = async () => {
    if (specInfo.capacityNeed === '' || specInfo.capacityFutureNeed === '') {
      return;
    }
    if (specInfo.capacityNeed > 0 && specInfo.capacityFutureNeed > 0) {
      isTableLoading.value = true;
      const clusterType = props.data?.clusterType ?? ClusterTypes.TWEMPROXY_REDIS_INSTANCE;
      const params = {
        spec_cluster_type: clusterType,
        spec_machine_type: ClusterMachineMap[clusterType],
        shard_num: props.data.shardNum === 0 ? undefined : props.data.shardNum,
        capacity: specInfo.capacityNeed,
        future_capacity: specInfo.capacityNeed <= specInfo.capacityFutureNeed ? specInfo.capacityFutureNeed : specInfo.capacityNeed,
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
  const handleConfirm = async () => {
    const index = radioValue.value;
    if (applySchema.value === APPLY_SCHEME.AUTO) {
      if (index !== -1) {
        handleClickConfirm()
      }
    } else {
      const validateResult = await formRef.value!.validate()
      if (validateResult) {
        handleClickConfirm()
      }
    }
  };

  const handleClickConfirm = () => {
    const result = {} as SpecResultInfo
    const capacityInfo = {} as CapacityNeed
    if (applySchema.value === APPLY_SCHEME.AUTO) {
      const index = radioValue.value;
      const choosedObj = tableData.value[index]
      Object.assign(result, {
        cluster_capacity: choosedObj.cluster_capacity,
        max: choosedObj.qps.max,
        cluster_shard_num: choosedObj.cluster_shard_num,
        spec_id: choosedObj.spec_id,
        machine_pair: choosedObj.machine_pair,
      })
      Object.assign(capacityInfo, {
        current: Number(specInfo.capacityNeed),
        future: Number(specInfo.capacityFutureNeed)
      })
    } else {
      Object.assign(result, {
        cluster_capacity: specInfo.totalCapcity,
        max: 0,
        cluster_shard_num: specInfo.clusterShardNum,
        spec_id: specInfo.specId,
        machine_pair: specInfo.count
      })
      Object.assign(capacityInfo, {
        current: specInfo.totalCapcity,
        future: specInfo.totalCapcity
      })
    }
    emits('click-confirm', result, capacityInfo);
  }

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
    color: #ea3636;
  }

  .negtive {
    color: #2dcb56;
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
      background: #fafbfd;

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
            color: #63656e;
            text-align: right;
          }

          .content {
            flex: 1;
            display: flex;
            font-size: 12px;
            color: #63656e;

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
              color: #63656e;
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

    .plan-form {
      :deep(.bk-form-label) {
        font-size: 12px;
      }
    }

    .input-box {
      display: flex;
      width: 100%;
      align-items: center;

      .num-input {
        width: 315px;
      }

      .uint {
        margin-left: 12px;
        font-size: 12px;
        color: #63656e;
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
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
