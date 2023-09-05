<template>
  <div class="cluster-spec-plan-selector">
    <div class="capacity-box">
      <DbFormItem
        :label="t('目标集群容量需求')"
        required>
        <BkInput
          v-model="localCapacity"
          :min="1"
          suffix="G"
          type="number" />
      </DbFormItem>
      <DbFormItem
        :label="t('未来集群容量需求')"
        required>
        <BkInput
          v-model="localFutureCapacity"
          :min="1"
          suffix="G"
          type="number" />
      </DbFormItem>
    </div>
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
    <DbFormItem :label="t('集群部署方案')">
      <BkLoading :loading="isPlanLoading">
        <BkTable
          :columns="tableColumns"
          :data="planList"
          @row-click="handleRowClick" />
      </BkLoading>
    </DbFormItem>
  </div>
</template>
<script setup lang="tsx">
  import {
    reactive,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/dbResource';
  import {
    type FilterClusterSpecItem,
    getFilterClusterSpec,
    queryQPSRange,
  } from '@services/resourceSpec';

  import { useGlobalBizs } from '@stores';

  export type IRowData = FilterClusterSpecItem

  interface Props {
    clusterType: string,
    machineType: string,
    cloudId: number
  }
  interface Emits{
    (e: 'change', modelValue: number, data: FilterClusterSpecItem): void
  }
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const modelValue = defineModel<number>('modelValue', {
    local: true,
  });
  const specData = defineModel<{name: string, futureCapacity: number}>('specData');

  const genSliderData = () => ({
    value: [0, 1],
    max: 1,
    min: 0,
    disabled: false,
  });
  const formatterLabel = (value: string) => `${value}/s`;

  const sliderProps = reactive(genSliderData());
  const localCapacity = ref(1);
  const localFutureCapacity = ref(1);
  const queryTimer = ref();
  const specCountMap = shallowRef<Record<number, number>>({});

  const tableColumns = [
    {
      field: 'spec_name',
      label: t('资源规格'),
      width: 200,
      render: ({ data }: { data: FilterClusterSpecItem}) => (
        <bk-radio
          label={data.spec_id}
          modelValue={modelValue.value}
          class="spec-radio">
          <div class="text-overflow" v-overflow-tips>{data.spec_name}</div>
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
      render: ({ data }: {data: FilterClusterSpecItem}) => {
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
      if (!max || !min) {
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
    data: planList,
    run: fetchPlanList,
  } = useRequest(getFilterClusterSpec, {
    debounceOptions: {
      maxWait: 2000,
      trailing: true,
    },
    manual: true,
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
      futureCapacity: localFutureCapacity.value,
    };
  });

  watch(planList, () => {
    if (!planList.value || planList.value.length < 1) {
      return;
    }
    fetchSpecCount({
      resource_type: props.clusterType,
      bk_biz_id: currentBizId,
      bk_cloud_id: props.cloudId,
      spec_ids: planList.value.map(item => item.spec_id),
    });
  }, {
    immediate: true,
  });

  watch(() => sliderProps.value, (data) => {
    clearTimeout(queryTimer.value);
    queryTimer.value = setTimeout(() => {
      handleDpsRangChange(data as [number, number]);
    }, 1000);
  }, {
    immediate: true,
  });

  const handleDpsRangChange = (data: [number, number]) => {
    const [min, max] = data;
    fetchPlanList({
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      capacity: localCapacity.value,
      future_capacity: localFutureCapacity.value,
      qps: { min, max },
    });
  };

  // 选中单行
  const handleRowClick = (event: MouseEvent, data: FilterClusterSpecItem) => {
    modelValue.value = data.spec_id;
    specData.value = {
      name: data.spec_name,
      futureCapacity: localFutureCapacity.value,
    };
    emits('change', data.spec_id, data);
  };

</script>
<style lang="less">
  .cluster-spec-plan-selector {
    display: block;

    .capacity-box{
      display: flex;

      .bk-form-item{
        flex: 1;

        &~.bk-form-item{
          margin-left:40px;
        }
      }
    }
  }
</style>
