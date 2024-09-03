<template>
  <div class="cluster-spec-plan-selector">
    <DbFormItem
      :label="t('部署方案选择')"
      required>
      <BkRadioGroup
        v-model="applyType"
        style="width: 314px">
        <BkRadioButton
          label="auto"
          style="flex: 1">
          {{ t('自动推荐方案') }}
          <BkTag
            size="small"
            theme="success">
            {{ t('实验') }}
          </BkTag>
        </BkRadioButton>
        <BkRadioButton
          label="custom"
          style="flex: 1">
          {{ t('自定义方案') }}
        </BkRadioButton>
      </BkRadioGroup>
    </DbFormItem>
    <template v-if="applyType === 'auto'">
      <DbFormItem
        :label="t('目标集群容量需求')"
        required>
        <BkInput
          v-model="localCapacity"
          style="width: 314px"
          type="number" />
        <span class="input-desc">G</span>
      </DbFormItem>
      <DbFormItem
        :label="t('未来集群容量需求')"
        required>
        <BkInput
          v-model="localFutureCapacity"
          style="width: 314px"
          type="number" />
        <span class="input-desc">G</span>
      </DbFormItem>
      <DbFormItem
        :label="t('QPS 预估范围')"
        required>
        <BkLoading :loading="isDpsRangLoading">
          <BkSlider
            v-model="sliderProps.value"
            :disable="sliderProps.disabled"
            :formatter-label="formatterLabel"
            :max-value="sliderProps.max"
            :min-value="sliderProps.min"
            range
            show-between-label
            show-input
            show-tip
            style="padding-left: 6px" />
        </BkLoading>
      </DbFormItem>
      <DbFormItem
        v-bind="planFormItemProps"
        :label="t('集群部署方案')">
        <BkLoading :loading="isPlanLoading">
          <BkTable
            :columns="tableColumns"
            :data="planList"
            @row-click="(event: MouseEvent, data: TicketSpecInfo) => handleRowClick(data)" />
        </BkLoading>
      </DbFormItem>
    </template>
    <template v-else>
      <BkFormItem
        :label="t('规格')"
        property="specId"
        required>
        <SpecSelector
          ref="specSelectorRef"
          v-model="customSpecInfo.specId"
          :biz-id="currentBizId"
          :clearable="false"
          :cloud-id="cloudId"
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          machine-type="remote"
          style="width: 314px" />
      </BkFormItem>
      <BkFormItem
        :label="t('数量')"
        property="count"
        required
        :rules="countRules">
        <BkInput
          v-model="customSpecInfo.count"
          clearable
          :max="clusterShardNum"
          :min="1"
          show-clear-only-hover
          style="width: 314px"
          type="number" />
        <span class="input-desc">{{ t('组') }}</span>
      </BkFormItem>
      <BkFormItem
        :label="t('单机分片数')"
        required>
        <BkInput
          v-model="localRemoteShardNum"
          disabled
          style="width: 314px"
          type="number" />
      </BkFormItem>
      <BkFormItem
        :label="t('集群分片数')"
        required>
        <BkInput
          v-model="localClusterShardNum"
          disabled
          style="width: 314px"
          type="number" />
      </BkFormItem>
      <BkFormItem
        :label="t('总容量')"
        :required="false">
        <BkInput
          v-model="specInfo.totalCapcity"
          disabled
          :placeholder="t('自动生成')"
          style="width: 314px"
          type="number" />
        <span class="input-desc">G</span>
      </BkFormItem>
      <BkFormItem
        :label="t('QPS')"
        :required="false">
        <BkInput
          v-model="specInfo.qps"
          disabled
          :placeholder="t('自动生成')"
          style="width: 314px"
          type="number" />
        <span class="input-desc">/s</span>
      </BkFormItem>
    </template>
  </div>
</template>
<script setup lang="tsx">
  import type { FormItemProps } from 'bkui-vue/lib/form/form-item';
  import _ from 'lodash';
  import {
    reactive,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import {
    getFilterClusterSpec,
    queryQPSRange,
  } from '@services/source/dbresourceSpec';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import SpecSelector from '@components/apply-items/SpecSelector.vue';

  export type TicketSpecInfo = Pick<ClusterSpecModel, 'spec_id' | 'spec_name' | 'cluster_capacity' | 'machine_pair'>

  interface Props {
    clusterType: string,
    machineType: string,
    cloudId: number,
    clusterShardNum: number,
    planFormItemProps?: Partial<FormItemProps>,
  }

  interface Emits{
    (e: 'change', modelValue: number, data: TicketSpecInfo): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const modelValue = defineModel<number>('modelValue');
  const specData = defineModel<{name: string, futureCapacity: number}>('specData');
  const customSpecInfo = defineModel<{
    specId: string | number,
    count: number
  }>('customSpecInfo', {
    required: true
  });

  const genSliderData = () => ({
    value: [0, 1],
    max: 1,
    min: 0,
    disabled: false,
  });
  const formatterLabel = (value: string) => `${value}/s`;

  const specSelectorRef = ref<InstanceType<typeof SpecSelector>>()
  const localCapacity = ref();
  const localFutureCapacity = ref();
  const localClusterShardNum = ref();
  const queryTimer = ref();
  const applyType = ref('auto')

  const sliderProps = reactive(genSliderData());

  const specCountMap = shallowRef<Record<number, number>>({});
  const planList = shallowRef<ServiceReturnType<typeof getFilterClusterSpec>>([]);

  const countRules = [
    {
      message: t('必须要能除尽总分片数'),
      trigger: 'change',
      validator: () => props.clusterShardNum % customSpecInfo.value.count === 0
    },
  ]

  const tableColumns = [
    {
      field: 'spec_name',
      label: t('资源规格'),
      width: 200,
      render: ({ data }: { data: ClusterSpecModel}) => (
        <bk-radio
          label={data.spec_id}
          modelValue={modelValue.value}
          style="display: flex"
          onClick={() => handleRowClick(data)}>
          <div
            class="text-overflow"
            v-overflow-tips
            onClick={(event: Event) => event.stopPropagation()}>
            {data.spec_name}
          </div>
        </bk-radio>
      ),
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
      label: t('集群容量G'),
      sort: true,
    },
    {
      field: 'cluster_qps',
      label: t('集群QPS每秒'),
    },
    {
      field: 'count',
      label: t('可用主机数'),
      render: ({ data }: {data: ClusterSpecModel}) => {
        if (isCountLoading.value) {
          return (
            <div class="rotate-loading" style="display: inline-block;">
              <db-icon type="sync-pending" />
            </div>
          );
        }
        return `${specCountMap.value[data.spec_id]}`;
      },
    },
  ];

  const specInfo = computed(() => {
    const data = specSelectorRef.value?.getData()
    const {count} = customSpecInfo.value

    if (_.isEmpty(data)) {
      return {
        totalCapcity: '',
        qps: ''
      }
    }

    return {
      totalCapcity: count * getSpecCapacity(data.storage_spec),
      qps: count * (data.qps.min ?? 0)
    }
  })

  const localRemoteShardNum = computed(() => props.clusterShardNum / customSpecInfo.value.count)

  const getSpecCapacity = (storageSpec: ResourceSpecModel['storage_spec']) => {
    let specCapacity = 0
    for (let i = 0; i < storageSpec.length; i++) {
      const storageSpecItem = storageSpec[i]
      if (storageSpecItem.mount_point === '/data1') {
        return storageSpecItem.size
      }
      if (storageSpecItem.mount_point === '/data') {
        specCapacity = storageSpecItem.size / 2
      }
    }
    return specCapacity
  }

  // QPS 范围
  const {
    loading: isDpsRangLoading,
    run: fetchQpsRang,
  } = useRequest(queryQPSRange, {
    manual: true,
    debounceOptions: {
      maxWait: 20000,
      trailing: true,
    },
    onSuccess({ max, min }) {
      if (!max && !min) {
        sliderProps.max = 0;
        sliderProps.min = 0;
        sliderProps.disabled = true;
        return;
      }

      sliderProps.value = [min, max];
      sliderProps.max = max;
      sliderProps.min = min;
      sliderProps.disabled = false;
    },
  });

  // 规格列表
  const {
    loading: isPlanLoading,
    run: fetchPlanList,
  } = useRequest(getFilterClusterSpec, {
    debounceOptions: {
      maxWait: 2000,
      trailing: true,
    },
    manual: true,
    onSuccess(data) {
      if (props.clusterShardNum && props.clusterShardNum > 0) {
        planList.value = _.filter(data, item => item.cluster_shard_num === props.clusterShardNum);
      } else {
        planList.value = data;
      }
    },
  });

  // 可用主机数
  const {
    loading: isCountLoading,
    run: fetchSpecCount,
  } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specCountMap.value = data;
    },
  });

  watch(() => [props.clusterType, props.machineType], () => {
    Object.assign(sliderProps, genSliderData());
    planList.value = [];
  });

  watch([localCapacity, localFutureCapacity], () => {
    if (!localCapacity.value || !localFutureCapacity.value) {
      return;
    }
    fetchQpsRang({
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      capacity: localCapacity.value,
      future_capacity: localFutureCapacity.value,
    });
    modelValue.value = undefined;
    specData.value = {
      name: '',
      futureCapacity: 0,
    };
  });

  watch(planList, () => {
    if (!planList.value || planList.value.length < 1) {
      return;
    }
    fetchSpecCount({
      bk_biz_id: currentBizId,
      bk_cloud_id: props.cloudId,
      spec_ids: planList.value.map(item => item.spec_id),
    });
  }, {
    immediate: true,
  });

  watch(() => sliderProps.value, (data) => {
    if (!localCapacity.value || !localFutureCapacity.value) {
      return;
    }
    clearTimeout(queryTimer.value);
    queryTimer.value = setTimeout(() => {
      handleDpsRangChange(data as [number, number]);
    }, 1000);
  });

  watch(() => props.clusterShardNum, () => {
    localClusterShardNum.value = props.clusterShardNum
  }, {
    immediate: true
  })

  watch([() => customSpecInfo.value.count, () => customSpecInfo.value.specId], ([count, specId]) => {
    nextTick(() => {
      const data = specSelectorRef.value?.getData()
      if(!_.isEmpty(data)) {
        handleRowClick({
          spec_id: Number(specId),
          spec_name: data.spec_name,
          cluster_capacity: count * getSpecCapacity(data.storage_spec),
          machine_pair: customSpecInfo.value.count
        })
      }
    })
  }, {
    immediate: true
  })

  const handleDpsRangChange = (data: [number, number]) => {
    const [min, max] = data;
    fetchPlanList({
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      capacity: localCapacity.value,
      future_capacity: localFutureCapacity.value,
      qps: { min, max },
      shard_num: props.clusterShardNum,
    });
  };

  // 选中单行
  const handleRowClick = (data?: TicketSpecInfo) => {
    if (data) {
      modelValue.value = data.spec_id;
      specData.value = {
        name: data.spec_name,
        futureCapacity: data.cluster_capacity,
      };
      emits('change', data.spec_id, {
        spec_id: data.spec_id,
        spec_name: data.spec_name,
        cluster_capacity: data.cluster_capacity,
        machine_pair: data.machine_pair
      });
    }

  };
</script>
<style lang="less">
  .cluster-spec-plan-selector {
    display: block;

    // .capacity-box {
    //   display: flex;

    //   .bk-form-item {
    //     flex: 1;

    //     & ~ .bk-form-item {
    //       margin-left: 40px;
    //     }
    //   }
    // }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }
  }
</style>
