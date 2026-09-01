<template>
  <div class="redis-backend-spec">
    <ApplySchema v-model="applySchema" />
    <template v-if="applySchema === APPLY_SCHEME.AUTO">
      <BkFormItem
        :label="targetCapacityTitle"
        property="details.resource_spec.backend_group.capacity"
        required>
        <DbInput
          allow-empty-value
          :min="1"
          :model-value="modelValue.capacity"
          style="width: 314px"
          type="number"
          @change="handleChangeCapacity" />
        <span class="input-desc">G</span>
      </BkFormItem>
      <BkFormItem
        :label="futureCapacityTitle"
        property="details.resource_spec.backend_group.future_capacity"
        required>
        <DbInput
          allow-empty-value
          :min="Number(modelValue.capacity)"
          :model-value="modelValue.future_capacity"
          style="width: 314px"
          type="number"
          @change="handleChangeFutureCapacity" />
        <span class="input-desc">G</span>
      </BkFormItem>
      <ResourcePreview
        v-model:tag-list="modelValue.labels"
        :biz-id="bizId"
        :params="{
          city: cityName,
          subzones: subzoneNames.join('，'),
          subzone_ids: subzoneIds.join(','),
          for_bizs: bizId ? [bizId, 0] : [0],
          resource_types: [DBTypes.REDIS, 'PUBLIC'],
          spec_id: Number(modelValue.spec_id),
          labels: modelValue.labels.map((item) => item.id).join(','),
        }"
        property="details.resource_spec.backend_group.labels" />
      <BkFormItem
        ref="specRef"
        :label="t('集群部署方案')"
        property="details.resource_spec.backend_group.spec_id"
        required>
        <PrimaryTable
          v-bkloading="{ loading: isLoading }"
          class="custom-edit-table"
          :columns="columns"
          :data="specs"
          row-key="spec_id"
          @row-click="handleRowClick">
          <template #empty>
            <p
              v-if="!modelValue.capacity || !modelValue.future_capacity"
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
        </PrimaryTable>
      </BkFormItem>
    </template>
    <CustomSchema
      v-else
      ref="customSchemaRef"
      v-model="modelValue"
      :biz-id="bizId"
      :city-code="cityCode"
      :city-name="cityName"
      :cloud-id="cloudId"
      :cluster-type="clusterType"
      :machine-type="machineType"
      :subzone-ids="subzoneIds"
      :subzone-names="subzoneNames" />
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { PrimaryTableCol, TableRowData } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getFilterClusterSpec } from '@services/source/dbresourceSpec';

  import { ClusterTypes, DBTypes } from '@common/const';

  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import ApplySchema, { APPLY_SCHEME } from '@views/db-manage/common/apply-schema/Index.vue';

  import CustomSchema from './components/CustomSchema.vue';

  interface ModelValue {
    capacity: number | string;
    count: number | string;
    future_capacity: number | string;
    labels: {
      id: number;
      value: string;
    }[];
    spec_id: number | '';
  }

  interface Props {
    bizId: number | '';
    cityCode: string;
    cityName: string;
    cloudId: number | string;
    clusterType: string;
    machineType: string;
    subzoneIds: number[];
    subzoneNames: string[];
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<ModelValue>({ required: true });
  const applySchema = defineModel<APPLY_SCHEME>('applySchema', { required: true });

  const { t } = useI18n();

  const specRef = ref();
  const customSchemaRef = ref<InstanceType<typeof CustomSchema>>();
  const isLoading = ref(false);

  const specs = shallowRef<ClusterSpecModel[]>([]);
  const countMap = shallowRef({} as Record<number, number>);

  const isMemoryType = computed(() =>
    [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.TWEMPROXY_REDIS_INSTANCE].includes(
      props.clusterType as ClusterTypes,
    ),
  );
  const targetCapacityTitle = computed(() =>
    isMemoryType.value ? t('集群容量需求(内存容量)') : t('集群容量需求(磁盘容量)'),
  );
  const futureCapacityTitle = computed(() =>
    isMemoryType.value ? t('未来集群容量需求(内存容量)') : t('未来集群容量需求(磁盘容量)'),
  );

  const columns: PrimaryTableCol[] = [
    {
      cell: (_, { row }) => (
        <bk-radio
          v-model={modelValue.value.spec_id}
          class='spec-radio'
          label={row.spec_id}>
          {row.spec_name}
        </bk-radio>
      ),
      colKey: 'spec_name',
      title: t('资源规格'),
      width: 300,
    },
    {
      colKey: 'machine_pair',
      sorter: (a: TableRowData, b: TableRowData) => a.machine_pair - b.machine_pair,
      title: t('需机器组数'),
    },
    {
      colKey: 'cluster_shard_num',
      sorter: (a: TableRowData, b: TableRowData) => a.cluster_shard_num - b.cluster_shard_num,
      title: t('集群分片'),
    },
    {
      colKey: 'cluster_capacity',
      sorter: (a: TableRowData, b: TableRowData) => a.cluster_capacity - b.cluster_capacity,
      title: t('集群容量G'),
    },
    {
      cell: (_, { row }) => String(countMap.value[row.spec_id] || 0),
      colKey: 'count',
      title: t('可用主机数'),
    },
  ];

  let timer: NodeJS.Timeout;

  watch(
    () => modelValue.value.spec_id,
    () => {
      if (modelValue.value.spec_id) {
        specRef.value?.clearValidate();
      }
    },
  );

  watch(
    () => [props.bizId, props.cloudId, props.cityCode, props.subzoneIds, specs.value],
    () => {
      if (
        typeof props.bizId === 'number' &&
        props.bizId > 0 &&
        typeof props.cloudId === 'number' &&
        specs.value.length > 0 &&
        props.cityCode &&
        props.subzoneIds.length > 0
      ) {
        fetchSpecResourceCount();
      }
    },
    { deep: true, immediate: true },
  );

  watch(
    () => [modelValue.value.capacity, modelValue.value.future_capacity],
    ([capacityValue, futureCapacityValue]) => {
      if (capacityValue === '' || futureCapacityValue === '') {
        resetSlider();
      } else {
        modelValue.value.spec_id = '';
        clearTimeout(timer);
        timer = setTimeout(() => {
          fetchFilterClusterSpec();
        }, 400);
      }
    },
  );

  const resetSlider = () => {
    specs.value = [];
  };

  const fetchFilterClusterSpec = () => {
    const { capacity, future_capacity: futureCapacity } = modelValue.value;

    if (!capacity || !futureCapacity) {
      return;
    }

    isLoading.value = true;
    getFilterClusterSpec({
      capacity: Number(capacity),
      future_capacity: Number(futureCapacity),
      spec_cluster_type: 'redis',
      spec_machine_type: props.machineType,
    })
      .then((res) => {
        specs.value = res;
      })
      .catch(() => {
        specs.value = [];
      })
      .finally(() => {
        isLoading.value = false;
        countMap.value = {};
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
      city: props.cityCode,
      spec_ids: specs.value.map((item) => item.spec_id),
      sub_zone_ids: props.subzoneIds.map((item) => `${item}`),
    }).then((data) => {
      countMap.value = data;
    });
  }, 100);

  const handleRowClick = ({ row }: { row: TableRowData }) => {
    modelValue.value.spec_id = row.spec_id;
  };

  defineExpose({
    getData() {
      if (applySchema.value === APPLY_SCHEME.AUTO) {
        const item = specs.value.find((item) => item.spec_id === Number(modelValue.value.spec_id));
        if (item) {
          return item;
        }
        return {};
      }

      return customSchemaRef.value?.getInfo();
    },
  });
</script>

<style lang="less">
  .redis-backend-spec {
    max-width: 1200px;
    padding: 24px 24px 24px 10px;
    background-color: #f5f7fa;
    border-radius: 2px;

    .bk-form-item {
      .bk-form-content {
        .bk-select,
        .dbm-input {
          width: 314px !important;
        }
      }
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    .spec-radio {
      display: flex !important;
      max-width: 100%;

      .bk-radio-input {
        flex-shrink: 0;
        width: 16px;
      }

      .bk-radio-label {
        flex: 1;
        font-size: 12px;
      }
    }
  }
</style>
