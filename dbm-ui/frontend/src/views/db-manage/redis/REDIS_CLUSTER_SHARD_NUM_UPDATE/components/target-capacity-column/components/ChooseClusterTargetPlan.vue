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
  <div class="choose-cluster-target-plan">
    <div class="capacity-panel">
      <div class="panel-row">
        <div class="panel-column">
          <div class="panel-title">{{ t('当前 Proxy 规格') }}：</div>
          <div class="panel-content">
            <RenderSpec
              :data="proxySpec"
              :hide-qps="!proxySpec?.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="panel-column">
          <div class="panel-title">{{ t('目标 Proxy 规格') }}：</div>
          <div class="panel-content">
            <span v-if="targetProxySpecInfo">
              <RenderSpec
                :data="targetProxySpecInfo"
                :hide-qps="!targetProxySpecInfo.qps.max"
                is-ignore-counts />
            </span>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
      <div class="panel-row">
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 70px">
            {{ t('当前 Proxy 数量') }}：
          </div>
          <div class="panel-content">
            <span class="panel-spec">{{ cluster.proxy.length }}</span>
          </div>
        </div>
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 82px">
            {{ t('目标 Proxy 数量') }}：
          </div>
          <div class="panel-content">
            <template v-if="specInfo.proxy.count">
              <span class="panel-spec">{{ specInfo.proxy.count }}</span>
              <ValueDiff
                :current-value="cluster.proxy.length"
                :show-rate="false"
                :target-value="specInfo.proxy.count" />
            </template>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
      <div class="panel-row">
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 70px">
            {{ t('当前使用率') }}：
          </div>
          <div class="panel-content">
            <span class="panel-spec">
              <ClusterCapacityUsageRate :cluster-stats="cluster.cluster_stats" />
            </span>
          </div>
        </div>
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 82px">
            {{ t('目标使用率') }}：
          </div>
          <div class="panel-content">
            <template v-if="targetInfo">
              <span class="panel-spec">
                <ClusterCapacityUsageRate :cluster-stats="targetClusterStats" />
                <ValueDiff
                  :current-value="convertStorageUnits(cluster.cluster_stats.total, 'B', 'GB')"
                  num-unit="G"
                  :target-value="targetInfo.capacity" />
              </span>
            </template>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
      <div class="panel-row">
        <div class="panel-column">
          <div class="panel-title">{{ t('当前后端存储规格') }}：</div>
          <div class="panel-content">
            <RenderSpec
              :data="backendSpec"
              :hide-qps="!backendSpec.qps.max"
              is-ignore-counts />
          </div>
        </div>
        <div class="panel-column">
          <div class="panel-title">{{ t('目标后端存储规格') }}：</div>
          <div class="panel-content">
            <template v-if="targetBackendSpecInfo">
              <RenderSpec
                :data="targetBackendSpecInfo"
                :hide-qps="!targetBackendSpecInfo?.qps.max"
                is-ignore-counts />
            </template>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
      <div class="panel-row">
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 70px">
            {{ t('当前机器组数') }}：
          </div>
          <div class="panel-content">
            <span class="panel-spec">{{ cluster.machine_pair_cnt }}</span>
          </div>
        </div>
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 82px">
            {{ t('目标机器组数') }}：
          </div>
          <div class="panel-content">
            <template v-if="targetInfo">
              <span class="panel-spec">{{ targetInfo.machinePairCount }}</span>
              <ValueDiff
                :current-value="cluster.machine_pair_cnt"
                :show-rate="false"
                :target-value="targetInfo.machinePairCount" />
            </template>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
      <div class="panel-row">
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 70px">
            {{ t('当前机器数量') }}：
          </div>
          <div class="panel-content">
            <span class="panel-spec"> {{ cluster.machine_pair_cnt * 2 }}</span>
          </div>
        </div>
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 82px">
            {{ t('目标机器数量') }}：
          </div>
          <div class="panel-content">
            <template v-if="targetInfo">
              <span class="panel-spec">{{ targetInfo.machinePairCount * 2 }}</span>
              <ValueDiff
                :current-value="cluster.machine_pair_cnt * 2"
                :show-rate="false"
                :target-value="targetInfo.machinePairCount * 2" />
            </template>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
      <div class="panel-row">
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 70px">
            {{ t('当前分片数') }}：
          </div>
          <div class="panel-content">
            <span class="panel-spec">{{ cluster.cluster_shard_num }}</span>
          </div>
        </div>
        <div class="panel-column">
          <div
            class="panel-title"
            style="min-width: 82px">
            {{ t('目标分片数') }}：
          </div>
          <div class="panel-content">
            <template v-if="targetInfo">
              <span class="panel-spec">{{ targetInfo.shardNum }}</span>
              <ValueDiff
                :current-value="cluster.cluster_shard_num"
                :show-rate="false"
                :target-value="targetInfo.shardNum" />
            </template>
            <span
              v-else
              style="color: #c4c6cc">
              --
            </span>
          </div>
        </div>
      </div>
    </div>
    <DbForm
      ref="formRef"
      class="plan-form"
      :label-width="200"
      :model="specInfo">
      <div class="title-spot mb-8">{{ t('Proxy 规格') }}<span class="required" /></div>
      <BkFormItem
        :label="t('规格')"
        property="proxy.spec_id"
        required>
        <SpecSelector
          ref="specProxyRef"
          v-model="specInfo.proxy.spec_id"
          :biz-id="cluster.bk_biz_id"
          :city="cluster.city_code"
          :clearable="false"
          :cloud-id="cluster.bk_cloud_id"
          :cluster-type="DBTypes.REDIS"
          machine-type="proxy"
          style="width: 314px" />
      </BkFormItem>
      <BkFormItem
        :label="t('数量')"
        property="proxy.count"
        required>
        <BkInput
          v-model="specInfo.proxy.count"
          :min="2"
          style="width: 314px"
          type="number" />
        <span class="input-desc">{{ t('至少n台', { n: 2 }) }}</span>
      </BkFormItem>
      <div class="title-spot mb-8">{{ t('集群部署方案') }}<span class="required" /></div>
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
            <div class="panel-unit">G</div>
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
            <div class="panel-unit">G</div>
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
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { ClusterTypes, DBTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue';
  import RenderSpec from '@components/render-table/columns/spec-display/Index.vue';

  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import ApplySchema, { APPLY_SCHEME } from '@views/db-manage/common/apply-schema/Index.vue';
  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';
  import CustomSchema from '@views/db-manage/redis/common/cluster-deploy-plan/CustomSchema.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';

  import { convertStorageUnits } from '@utils';

  export interface Props {
    cluster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      city_code: string;
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_stats: RedisModel['cluster_stats'];
      cluster_type: string;
      id: number;
      machine_pair_cnt: number;
      master_domain: string;
      proxy: RedisModel['proxy'];
    };
    targetSpec: {
      backend_group: {
        count: number;
        id: number;
      };
      capacity: number;
      cluster_shard_num: number;
      future_capacity: number;
    };
  }

  export interface CapacityNeed {
    current: number;
    future: number;
  }

  export interface SpecResultInfo {
    backend_spec: UnwrapRef<typeof targetBackendSpecInfo>;
    cluster_capacity: number;
    cluster_shard_num: number;
    proxy_spec: UnwrapRef<typeof targetProxySpecInfo>;
  }

  type FilterClusterSpecItem = ServiceReturnType<typeof getFilterClusterSpec>[0];

  interface Emits {
    (e: 'click-confirm', obj: SpecResultInfo, capacity: CapacityNeed): void;
    (e: 'click-cancel'): void;
  }

  interface Expose {
    submit: () => Promise<boolean>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const disabledConfirm = defineModel<boolean>('disabledConfirm', {
    required: true,
  });

  const { t } = useI18n();

  const specProxyRef = useTemplateRef('specProxyRef');

  const formRef = ref<InstanceType<typeof DbForm>>();
  const customSchemaRef = ref<InstanceType<typeof CustomSchema>>();
  const radioValue = ref(-1);
  const radioChoosedId = ref(''); // 标记，sort重新定位index用
  const isTableLoading = ref(false);
  const tableData = ref<FilterClusterSpecItem[]>([]);
  // const targetCapacity = ref({
  //   current: props.cluster.cluster_capacity ?? 1,
  //   total: 1,
  // });
  const applySchema = ref(APPLY_SCHEME.AUTO);

  const targetProxySpecInfo = shallowRef<{ id: number } & ComponentProps<typeof RenderSpec>['data']>();
  const targetBackendSpecInfo = shallowRef<{ id: number } & ComponentProps<typeof RenderSpec>['data']>();

  const specInfo = reactive({
    capacityFutureNeed: '' as number | '',
    capacityNeed: '' as number | '',
    clusterShardNum: 1,
    count: 1,
    proxy: {
      count: 2,
      spec_id: '',
    },
    shardNum: 1,
    specId: '',
    totalCapcity: 0,
  });

  const clusterInfo = reactive({
    bizId: 0,
    cloudId: 0,
    clusterType: '',
    machineType: '',
  });

  const futrueCapacityRule = [
    {
      message: t('未来容量必须大于等于目标容量'),
      trigger: 'change',
      validator: (value: number) => value < Number(specInfo.capacityNeed || 0),
    },
  ];

  const isMemoryType = computed(() =>
    [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.TWEMPROXY_REDIS_INSTANCE].includes(
      props.cluster.cluster_type as ClusterTypes,
    ),
  );
  const targetCapacityTitle = computed(() =>
    isMemoryType.value ? t('目标集群容量需求(内存容量)') : t('目标集群容量需求(磁盘容量)'),
  );
  const futureCapacityTitle = computed(() =>
    isMemoryType.value ? t('未来集群容量需求(内存容量)') : t('未来集群容量需求(磁盘容量)'),
  );

  const proxySpec = computed(() => props.cluster.proxy[0].spec_config);
  const backendSpec = computed(() => ({
    ...props.cluster.cluster_spec,
    name: props.cluster.cluster_spec.spec_name,
  }));

  const targetInfo = computed(() => {
    if (applySchema.value === APPLY_SCHEME.AUTO) {
      if (radioValue.value === -1) {
        return;
      }
      const plan = tableData.value[radioValue.value];
      return {
        backendSpecName: plan.spec_name,
        capacity: plan.cluster_capacity,
        machinePairCount: plan.machine_pair,
        shardNum: plan.cluster_shard_num,
      };
    }
    return {
      backendSpecName: customSchemaRef.value?.getInfo().spec_name,
      capacity: specInfo.totalCapcity,
      machinePairCount: specInfo.count,
      shardNum: specInfo.clusterShardNum,
    };
  });

  const targetClusterStats = computed(() => {
    let stats = {} as RedisModel['cluster_stats'];
    if (!_.isEmpty(props.cluster.cluster_stats)) {
      const { used = 0 } = props.cluster.cluster_stats;
      const targetTotal = convertStorageUnits(targetInfo.value?.capacity ?? 0, 'GB', 'B');

      stats = {
        in_use: Number(((used / targetTotal) * 100).toFixed(2)),
        total: targetTotal,
        used,
      };
    }

    // emits('targetStatsChange', stats);
    return stats;
  });

  const columns = computed(() => {
    const totalColums = [
      {
        field: 'spec',
        label: t('资源规格'),
        render: ({ index, row }: { index: number; row: ClusterSpecModel }) => (
          <div style='display:flex;align-items:center;'>
            <bk-radio
              v-model={radioValue.value}
              label={index}>
              {row.spec_name}
            </bk-radio>
          </div>
        ),
        showOverflowTooltip: true,
        width: 260,
      },
      {
        field: 'machine_pair',
        label: t('需机器组数'),
        sort: true,
      },
      {
        field: 'cluster_shard_num',
        label: t('集群分片'),
        sort: true,
      },
      {
        field: 'cluster_capacity',
        label: t('集群容量(G)'),
        sort: true,
      },
    ];
    return totalColums;
  });

  let rawTableData: FilterClusterSpecItem[] = [];

  watch(
    () => props.cluster,
    () => {
      // targetCapacity.value.current = props.cluster.cluster_capacity;
      Object.assign(specInfo, {
        clusterShardNum: props.targetSpec.cluster_shard_num,
        count: props.targetSpec.backend_group.count,
        // shardNum: props.targetSpec.cluster_shard_num / props.targetSpec.count,
      });
      Object.assign(clusterInfo, {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        cloudId: props.cluster.bk_cloud_id,
        clusterType: props.cluster.cluster_type,
        machineType: specClusterMachineMap[props.cluster.cluster_type],
      });
    },
    {
      immediate: true,
    },
  );

  watch(
    () => specInfo.capacityNeed,
    (data) => {
      if (data && data > 0 && data !== specInfo.capacityFutureNeed) {
        specInfo.capacityFutureNeed = data;
      }
    },
    {
      immediate: true,
    },
  );

  watch(radioValue, (index) => {
    if (index === -1) {
      return;
    }

    const plan = tableData.value[index];
    targetBackendSpecInfo.value = {
      ...plan,
      id: plan.spec_id,
      name: plan.spec_name,
    };
    // targetCapacity.value.total = plan.cluster_capacity;
    // targetBackendSpec.value = plan.spec_name;
  });

  watch(
    () => specInfo.specId,
    () => {
      nextTick(() => {
        if (applySchema.value !== APPLY_SCHEME.AUTO) {
          // targetCapacity.value.total = specInfo.totalCapcity;
          const customSchemaInfo = customSchemaRef.value!.getInfo();
          targetBackendSpecInfo.value = {
            ...customSchemaInfo,
            id: Number(specInfo.specId),
            name: customSchemaInfo.spec_name,
          };
        }
      });
    },
  );

  watch(
    () => specInfo.proxy.spec_id,
    () => {
      nextTick(() => {
        const specProxyRefInfo = specProxyRef.value!.getData();
        targetProxySpecInfo.value = {
          ...specProxyRefInfo,
          id: Number(specInfo.proxy.spec_id),
          name: specProxyRefInfo.spec_name,
        };
      });
    },
  );

  watch(
    [applySchema, radioValue],
    () => {
      disabledConfirm.value = applySchema.value === APPLY_SCHEME.AUTO && radioValue.value === -1;
    },
    {
      immediate: true,
    },
  );

  const handleSearchClusterSpec = async () => {
    if (specInfo.capacityNeed === '' || specInfo.capacityFutureNeed === '') {
      return;
    }
    if (specInfo.capacityNeed > 0 && specInfo.capacityFutureNeed > 0) {
      isTableLoading.value = true;
      const params = {
        capacity: specInfo.capacityNeed,
        future_capacity:
          specInfo.capacityNeed <= specInfo.capacityFutureNeed ? specInfo.capacityFutureNeed : specInfo.capacityNeed,
        spec_cluster_type: ClusterTypes.REDIS,
        spec_machine_type: props.cluster.cluster_type,
      };
      const retArr = await getFilterClusterSpec(params).finally(() => {
        isTableLoading.value = false;
      });
      radioValue.value = -1;
      radioChoosedId.value = '';
      tableData.value = retArr;
      rawTableData = _.cloneDeep(retArr);
    }
  };

  // 点击确定
  // const handleConfirm = async () => {
  //   const index = radioValue.value;
  //   if (applySchema.value === APPLY_SCHEME.AUTO) {
  //     if (index !== -1) {
  //       handleClickConfirm()
  //     }
  //   } else {
  //     const validateResult = await formRef.value!.validate()
  //     if (validateResult) {
  //       handleClickConfirm()
  //     }
  //   }
  // };

  const handleRowClick = (event: PointerEvent, row: FilterClusterSpecItem, index: number) => {
    radioValue.value = index;
    radioChoosedId.value = row.spec_name;
  };

  const handleColumnSort = (data: { column: { field: string }; index: number; type: string }) => {
    const { column, type } = data;
    const filed = column.field as keyof FilterClusterSpecItem;
    if (type === 'asc') {
      tableData.value.sort((prevItem, nextItem) => (prevItem[filed] as number) - (nextItem[filed] as number));
    } else if (type === 'desc') {
      tableData.value.sort((prevItem, nextItem) => (nextItem[filed] as number) - (prevItem[filed] as number));
    } else {
      tableData.value = rawTableData;
    }
    const index = tableData.value.findIndex((item) => item.spec_name === radioChoosedId.value);
    radioValue.value = index;
  };

  const handleClickConfirm = () => {
    const result = {} as SpecResultInfo;
    const capacityInfo = {} as CapacityNeed;
    const resultProxySpecInfo = {
      ...targetProxySpecInfo.value!,
      count: specInfo.proxy.count,
    };
    if (applySchema.value === APPLY_SCHEME.AUTO) {
      const index = radioValue.value;
      const choosedObj = tableData.value[index];
      Object.assign(result, {
        backend_spec: {
          ...targetBackendSpecInfo.value!,
          count: choosedObj.machine_pair,
        },
        cluster_capacity: choosedObj.cluster_capacity,
        cluster_shard_num: choosedObj.cluster_shard_num,
        proxy_spec: resultProxySpecInfo,
      });
      Object.assign(capacityInfo, {
        current: Number(specInfo.capacityNeed),
        future: choosedObj.cluster_capacity,
      });
    } else {
      Object.assign(result, {
        backend_spec: {
          ...targetBackendSpecInfo.value!,
          count: specInfo.count,
        },
        cluster_capacity: specInfo.totalCapcity,
        cluster_shard_num: specInfo.clusterShardNum,
        proxy_spec: resultProxySpecInfo,
      });
      Object.assign(capacityInfo, {
        current: props.cluster.cluster_capacity,
        future: specInfo.totalCapcity,
      });
    }
    emits('click-confirm', result, capacityInfo);
  };

  defineExpose<Expose>({
    async submit() {
      if (applySchema.value === APPLY_SCHEME.AUTO) {
        if (radioValue.value !== -1) {
          // handleClickConfirm();
          return formRef.value!.validate().then(() => {
            handleClickConfirm();
          });
        }
      } else {
        return formRef.value!.validate().then(() => {
          handleClickConfirm();
        });
      }
    },
  });
</script>

<style lang="less" scoped>
  .choose-cluster-target-plan {
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

        &:not(:first-child) {
          margin-top: 4px;
        }

        .panel-column {
          display: flex;
          width: 50%;
          align-items: center;

          .panel-title {
            width: 110px;
            height: 18px;
            font-size: 12px;
            line-height: 18px;
            letter-spacing: 0;
            color: #63656e;
            text-align: right;
          }

          .panel-content {
            flex: 1;
            display: flex;
            font-size: 12px;
            color: #63656e;

            .panel-percent {
              margin-left: 4px;
              font-size: 12px;
              font-weight: bold;
              color: #313238;
            }

            .panel-spec {
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

            .scale-percent-positive {
              color: #ea3636;
            }

            .scale-percent-negtive {
              color: #2dcb56;
            }

            :deep(.render-spec-box) {
              height: 22px;
              padding: 0;
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

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    .input-box {
      display: flex;
      width: 100%;
      align-items: center;

      .num-input {
        width: 315px;
      }

      .panel-unit {
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
