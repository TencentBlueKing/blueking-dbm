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
        :min="Number(modelValue.capacity)"
        :model-value="modelValue.future_capacity"
        style="width: 314px;"
        type="number"
        @change="handleChangeFutureCapacity" />
      <span class="input-desc">G</span>
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
        :data="renderSpecs"
        @row-click="handleRowClick">
        <template #empty>
          <p
            v-if="!modelValue.capacity || !modelValue.future_capacity"
            style="width: 100%; line-height: 128px; text-align: center;">
            <DbIcon
              class="mr-4"
              type="attention" />
            <span>{{ $t('请先设置容量') }}</span>
          </p>
          <BkException
            v-else
            :description="$t('无匹配的资源规格_请先修改容量设置')"
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

  import { getSpecResourceCount } from '@services/dbResource';
  import RedisClusterSpecModel from '@services/model/resource-spec/redis-cluster-sepc';
  import { getFilterClusterSpec } from '@services/resourceSpec';

  interface ModelValue {
    spec_id: number,
    capacity: number | string,
    count: number,
    future_capacity: number | string,
  }

  interface Props {
    clusterType: string,
    machineType: string,
    bizId: number | string,
    cloudId: number | string,
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<ModelValue>({ required: true });

  const { t } = useI18n();

  const specRef = ref();
  const specs = shallowRef<RedisClusterSpecModel[]>([]);
  const renderSpecs = shallowRef<RedisClusterSpecModel[]>([]);
  const isLoading = ref(false);
  const columns = [
    {
      field: 'spec_name',
      label: t('资源规格'),
      showOverflowTooltip: false,
      render: ({ data, index }: { data: RedisClusterSpecModel, index: number }) => (
        <bk-radio
          v-model={modelValue.value.spec_id}
          label={data.spec_id}
          kye={index}
          class="spec-radio">
          <div
            class="text-overflow"
            v-overflow-tips>
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
      field: 'count',
      label: t('可用主机数'),
    },
  ];

  let timer = 0;

  watch(() => modelValue.value.spec_id, () => {
    if (modelValue.value.spec_id) {
      specRef.value.clearValidate();
    }
  });

  watch([
    () => props.bizId,
    () => props.cloudId,
    specs,
  ], () => {
    if (
      typeof props.bizId === 'number'
      && props.bizId > 0
      && typeof props.cloudId === 'number'
      && specs.value.length > 0
    ) {
      fetchSpecResourceCount();
    }
  }, { immediate: true, deep: true });

  watch([
    () => modelValue.value.capacity,
    () => modelValue.value.future_capacity,
  ], ([capacityValue, futureCapacityValue]) => {
    if (capacityValue === '' || futureCapacityValue === '') {
      resetSlider();
    } else {
      modelValue.value.spec_id = -1;
      clearTimeout(timer);
      timer = setTimeout(() => {
        fetchFilterClusterSpec();
      }, 400);
    }
  });

  const resetSlider = () => {
    specs.value = [];
    renderSpecs.value = [];
  };

  const fetchFilterClusterSpec = () => {
    const { capacity, future_capacity: futureCapacity } = modelValue.value;

    if (!capacity || !futureCapacity) {
      return;
    }

    isLoading.value = true;
    getFilterClusterSpec({
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      capacity: Number(capacity),
      future_capacity: Number(futureCapacity),
    })
      .then((res) => {
        specs.value = res;
        renderSpecs.value = res;
      })
      .catch(() => {
        specs.value = [];
        renderSpecs.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const handleChangeCapacity = (value: string) => {
    if (value === '') {
      modelValue.value.capacity = value;
      return;
    }

    const capacityValue = Number(value);
    const futureCapacityValue = Number(modelValue.value.future_capacity);

    if (modelValue.value.future_capacity === '') {
      modelValue.value.capacity = capacityValue;
    } else {
      modelValue.value.capacity = capacityValue > futureCapacityValue ? futureCapacityValue : capacityValue;
    }
  };

  const handleChangeFutureCapacity = (value: string) => {
    if (value === '') {
      modelValue.value.future_capacity = value;
      return;
    }

    const futureCapacityValue = Number(value);
    const capacityValue = Number(modelValue.value.capacity);

    if (modelValue.value.future_capacity === '') {
      modelValue.value.future_capacity = futureCapacityValue;
    } else {
      modelValue.value.future_capacity = capacityValue > futureCapacityValue ? capacityValue : futureCapacityValue;
    }
  };

  const fetchSpecResourceCount = _.debounce(() => {
    getSpecResourceCount({
      bk_biz_id: Number(props.bizId),
      bk_cloud_id: Number(props.cloudId),
      spec_ids: specs.value.map(item => item.spec_id),
    }).then((data) => {
      renderSpecs.value = specs.value.map(item => ({
        ...item,
        count: data[item.spec_id] ?? 0,
      }));
    });
  }, 100);

  const handleRowClick = (event: Event, row: RedisClusterSpecModel) => {
    modelValue.value.spec_id = row.spec_id;
  };

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

    .custom-edit-table {
      :deep(.bk-table-body) {
        .cell {
          height: 42px !important;
        }

        tr:hover td {
          background-color: #f5f7fa !important;
        }
      }
    }
  }
</style>
