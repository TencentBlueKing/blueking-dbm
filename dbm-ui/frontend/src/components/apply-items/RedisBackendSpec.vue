<template>
  <div class="redis-backend-spec">
    <BkFormItem
      :label="$t('集群容量需求')"
      property="details.resource_spec.backend_group.capacity"
      required>
      <BkInput
        :min="1"
        :model-value="modelValue.capacity"
        style="width: 314px;"
        type="number"
        @change="handleChangeCapacity" />
      <span class="input-desc">G</span>
    </BkFormItem>
    <BkFormItem
      :label="$t('未来集群容量需求')"
      property="details.resource_spec.backend_group.future_capacity"
      required>
      <BkInput
        :min="modelValue.capacity"
        :model-value="modelValue.future_capacity"
        style="width: 314px;"
        type="number"
        @change="handleChangeFutureCapacity" />
      <span class="input-desc">G</span>
    </BkFormItem>
    <BkFormItem
      :label="$t('QPS预估范围')"
      required>
      <BkSlider
        v-model="sliderProps.value"
        :disable="sliderProps.disabled"
        :formatter-label="formatterLabel"
        :max-value="sliderProps.max"
        :min-value="sliderProps.min"
        range
        show-interval
        show-interval-label
        :step="sliderProps.step"
        style="width: 800px;font-size: 12px;" />
    </BkFormItem>
    <BkFormItem
      ref="specRef"
      :label="$t('集群部署方案')"
      property="details.resource_spec.backend_group.spec_id"
      required>
      <DbOriginalTable
        v-bkloading="{loading: isLoading}"
        class="custom-edit-table"
        :columns="columns"
        :data="specs">
        <template #empty>
          <p
            v-if="!sliderProps.value[1]"
            style="width: 100%; line-height: 128px; text-align: center;">
            <DbIcon
              class="mr-4"
              type="attention" />
            <span>{{ $t('请先设置容量及QPS范围') }}</span>
          </p>
          <BkException
            v-else
            :description="$t('无匹配的资源规格_请先修改容量及QPS设置')"
            scene="part"
            style="font-size: 12px;"
            type="empty" />
        </template>
      </DbOriginalTable>
    </BkFormItem>
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import {
    type FilterClusterSpecItem,
    getFilterClusterSpec,
    queryQPSRange,
  } from '@services/resourceSpec';

  interface TableRenderProps {
    data: FilterClusterSpecItem,
    row: FilterClusterSpecItem,
  }

  interface ModelValue {
    spec_id: string,
    capacity: number | string,
    future_capacity: number | string,
  }

  interface Props {
    clusterType: string,
    machineType: string,
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<ModelValue>({ required: true });

  const { t } = useI18n();

  const specRef = ref();
  const specs = shallowRef<FilterClusterSpecItem[]>([]);
  const isLoading = ref(false);
  const sliderProps = reactive({
    value: [0, 0],
    max: 0,
    min: 0,
    step: 1,
    disabled: true,
  });
  const columns = [
    {
      field: 'spec_name',
      label: t('资源规格'),
      render: ({ row }: TableRenderProps) => (
        <bk-radio
          v-model={modelValue.value.spec_id}
          label={row.spec_id}
          class="spec-radio">
          <div class="text-overflow" v-overflow-tips>{row.spec_name}</div>
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
      // sort: {
      //   sortFn: (a: FilterClusterSpecItem, b: FilterClusterSpecItem, type: 'desc' | 'asc' | 'null') => {
      //     if (type === 'null') return 0;
      //     const aQPS = a.qps.min * a.machine_pair;
      //     const bQPS = b.qps.min * b.machine_pair;
      //     return type === 'asc' ? aQPS - bQPS : bQPS - aQPS;
      //   },
      // },
      // render: ({ row }: TableRenderProps) => row.qps.min * row.machine_pair,
    },
  ];

  const formatterLabel = (value: string) => `${value}/s`;

  const resetSlider = () => {
    sliderProps.value = [0, 0];
    sliderProps.max = 0;
    sliderProps.min = 0;
    sliderProps.disabled = true;
    specs.value = [];
  };

  const getSliderStep = (min: number, max: number) => {
    const maxStep = 10;
    const difference = max - min;
    const getSeg = (nums: number): number => {
      const seg = nums / maxStep;
      if (seg > 10) {
        return getSeg(seg);
      }
      return Math.ceil(seg);
    };
    const step = getSeg(difference);

    return max / step;
  };

  const fetchQPSRange = _.debounce(() => {
    const { capacity, future_capacity: futureCapacity } = modelValue.value;
    if (!capacity || !futureCapacity) {
      resetSlider();
      return;
    }

    queryQPSRange({
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      capacity: Number(capacity),
      future_capacity: Number(futureCapacity),
    })
      .then(({ max, min }) => {
        if (!max || !min) {
          sliderProps.max = 0;
          sliderProps.min = 0;
          sliderProps.disabled = true;
        }
        sliderProps.value = [0, 0];
        sliderProps.max = max;
        sliderProps.min = min;
        sliderProps.disabled = false;
        sliderProps.step = getSliderStep(min, max);
      });
  }, 400);

  const fetchFilterClusterSpec = () => {
    const { capacity, future_capacity: futureCapacity } = modelValue.value;
    const [min, max] = sliderProps.value;

    if (!capacity || !futureCapacity || (max === 0)) {
      return;
    }

    isLoading.value = true;
    getFilterClusterSpec({
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      capacity: Number(capacity),
      future_capacity: Number(futureCapacity),
      qps: { min, max },
    })
      .then((res) => {
        specs.value = res;
      })
      .catch(() => {
        specs.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const handleChangeCapacity = (value: string) => {
    if (value === '') {
      modelValue.value.capacity = value;
      resetSlider();
      return;
    }

    const oldValue = modelValue.value.capacity;
    const capacityValue = Number(value);
    const futureCapacityValue = Number(modelValue.value.future_capacity);

    if (modelValue.value.future_capacity === '') {
      modelValue.value.capacity = capacityValue;
    } else {
      modelValue.value.capacity = capacityValue > futureCapacityValue ? futureCapacityValue : capacityValue;
    }

    if (oldValue !== modelValue.value.capacity && futureCapacityValue > 0) {
      fetchQPSRange();
    }
  };

  const handleChangeFutureCapacity = (value: string) => {
    if (value === '') {
      modelValue.value.future_capacity = value;
      resetSlider();
      return;
    }

    const oldValue = modelValue.value.future_capacity;
    const futureCapacityValue = Number(value);
    const capacityValue = Number(modelValue.value.capacity);

    if (modelValue.value.future_capacity === '') {
      modelValue.value.future_capacity = futureCapacityValue;
    } else {
      modelValue.value.future_capacity = capacityValue > futureCapacityValue ? capacityValue : futureCapacityValue;
    }

    if (oldValue !== modelValue.value.future_capacity && capacityValue > 0) {
      fetchQPSRange();
    }
  };

  watch(() => sliderProps.value, _.debounce(() => {
    modelValue.value.spec_id = '';
    if (sliderProps.value[1] > 0) {
      fetchFilterClusterSpec();
    } else {
      specs.value = [];
    }
  }, 400), { immediate: true, deep: true });

  watch(() => modelValue.value.spec_id, () => {
    if (modelValue.value.spec_id) {
      specRef.value.clearValidate();
    }
  });

  defineExpose({
    getData() {
      const item = specs.value.find(item => item.spec_id === Number(modelValue.value.spec_id));
      return item ?? {};
    },
  });
</script>

<style lang="less" scoped>
  .redis-backend-spec {
    max-width: 1200px;
    padding: 24px 24px 24px 0;
    background-color: #F5F7FA;
    border-radius: 2px;

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    :deep(.spec-radio) {
      max-width: 100%;
      overflow: hidden;

      .bk-radio-input {
        flex-shrink: 0;
      }

      .bk-radio-label {
        flex: 1;
        overflow: hidden;
      }
    }
  }
</style>
