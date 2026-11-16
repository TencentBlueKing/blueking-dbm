<template>
  <div class="spec-selector-wrapper">
    <DbSelect
      class="spec-selector"
      :clearable="clearable"
      filterable
      :loading="loading"
      :model-value="modelValue"
      @change="handleChange">
      <DbOption
        v-for="item in list"
        :key="item.spec_id"
        :label="item.spec_name"
        :value="item.spec_id">
        <SpecDetailPopover
          :data="item"
          placement="right-start">
          <div class="spec-display">
            <span class="text-overflow">{{ item.spec_name }}</span>
            <span
              v-if="typeof item.availableCount === 'number'"
              class="spec-display-count">
              {{ item.availableCount }}
            </span>
          </div>
        </SpecDetailPopover>
      </DbOption>
    </DbSelect>
    <DbIcon
      v-if="showRefreshIcon"
      v-bk-tooltips="t('刷新获取最新资源规格')"
      class="spec-refresh-icon"
      type="refresh"
      @click="getData" />
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { Affinity } from '@common/const';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  interface ResourceSpecData extends ResourceSpecModel {
    availableCount?: number;
    /** 按可用区分组的可用主机数（group_by_cloud_zone 时返回），供 popover 分组展示 */
    availableCountByZone?: Record<string, number>;
  }

  interface Props {
    bizId: number | string;
    city?: string;
    clearable?: boolean;
    cloudId: number | string;
    clusterType: string;
    // eslint-disable-next-line vue/require-default-prop
    disasterToleranceLevel?: string;
    machineType: string;
    modelValue: number | string;
    showRefresh?: boolean;
    // eslint-disable-next-line vue/require-default-prop
    subzoneIds?: string[] | number[];
  }

  type Emits = (e: 'update:modelValue', value: number | string) => void;

  interface Expose {
    getData: () => {
      instance_num?: number;
    } & Pick<ResourceSpecModel, 'spec_id' | 'spec_name' | 'cpu' | 'mem' | 'storage_spec' | 'qps' | 'capacity'>;
  }

  const props = withDefaults(defineProps<Props>(), {
    city: undefined,
    clearable: true,
    showRefresh: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const showRefreshIcon = computed(() => props.showRefresh && Boolean(props.clusterType && props.machineType));
  const list = shallowRef<ResourceSpecData[]>([]);
  const {
    data,
    loading,
    run: fetchData,
  } = useRequest(getResourceSpecList, {
    manual: true,
    onError: () => {
      list.value = [];
    },
    onSuccess: () => {
      list.value = data.value?.results ?? [];
      if (props.modelValue) {
        const isExist = list.value.some((item) => item.spec_id === props.modelValue);
        if (!isExist) {
          handleChange('');
        } else {
          handleChange(props.modelValue);
        }
      }
    },
  });

  const getData = () => {
    fetchData({
      biz_ids: `${props.bizId}`,
      enable: true,
      limit: -1,
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
    });
  };

  watch(
    () => [props.clusterType, props.machineType, props.bizId],
    () => {
      if (props.clusterType && props.machineType && props.bizId) {
        getData();
      }
    },
    { immediate: true },
  );

  const handleChange = (value: number | string) => {
    emits('update:modelValue', value);
  };

  const applySpecCount = (
    total: Record<number, number>,
    byCloudZone: Record<string, Record<number, number>> | null,
  ) => {
    list.value = list.value.map((item) =>
      Object.assign(item, {
        availableCount: total[item.spec_id],
        availableCountByZone: byCloudZone
          ? Object.fromEntries(Object.entries(byCloudZone).map(([zone, counts]) => [zone, counts[item.spec_id] ?? 0]))
          : undefined,
      }),
    );
  };

  const fetchSpecResourceCount = _.debounce(() => {
    const zoneNames = props.subzoneIds?.map((item) => `${item}`) ?? [];
    // 跨可用区（含强/弱）与指定可用区按可用区分组：选项外侧展示总数，popover 内按可用区展示各分得的主机数
    const isGroupByCloudZone = [
      Affinity.CROS_SUBZONE,
      Affinity.CROSS_SUBZONE_STRONG,
      Affinity.CROSS_SUBZONE_WEAK,
      Affinity.SAME_SUBZONE_CROSS_SWTICH,
    ].includes(props.disasterToleranceLevel as Affinity);
    const params: Omit<ServiceParameters<typeof getSpecResourceCount>, 'group_by_cloud_zone'> = {
      bk_biz_id: Number(props.bizId),
      bk_cloud_id: Number(props.cloudId),
      spec_ids: list.value.map((item) => item.spec_id),
    };
    if (props.city) {
      params.city = props.city;
    }
    // sub_zone_ids 存可用区名称，后端自行做「可用区 → 园区」展开；跨可用区随机时为空（不限可用区）
    if (zoneNames.length) {
      params.sub_zone_ids = zoneNames;
    }
    if (isGroupByCloudZone) {
      getSpecResourceCount({ ...params, group_by_cloud_zone: true }).then((data) => {
        applySpecCount(data.total, data.by_cloud_zone);
      });
    } else {
      getSpecResourceCount(params).then((data) => {
        applySpecCount(data, null);
      });
    }
  }, 100);

  watch(
    () => [props.bizId, props.cloudId, props.city, props.subzoneIds, props.disasterToleranceLevel, data.value],
    () => {
      if (
        typeof props.bizId === 'number' &&
        props.bizId > 0 &&
        typeof props.cloudId === 'number' &&
        data.value?.results?.length
      ) {
        fetchSpecResourceCount();
      }
    },
    { deep: true, immediate: true },
  );

  defineExpose<Expose>({
    getData() {
      const item = list.value.find((item) => item.spec_id === props.modelValue);
      if (item) {
        const { instance_num: instanceNum } = item;
        return {
          capacity: item.capacity,
          cpu: item.cpu,
          instance_num: instanceNum && instanceNum > 0 ? instanceNum : undefined,
          mem: item.mem,
          qps: item.qps,
          spec_id: item.spec_id,
          spec_name: item.spec_name,
          storage_spec: item.storage_spec,
        };
      }
      return {} as ReturnType<Expose['getData']>;
    },
  });
</script>
<style lang="less">
  .dbm-select-option {
    > span {
      display: block;
      width: 100%;
    }

    &.is-selected {
      .spec-display-count {
        color: white;
        background-color: #a3c5fd;
      }
    }
  }
</style>
<style lang="less" scoped>
  .spec-selector-wrapper {
    position: relative;
    display: inline-block;

    .spec-refresh-icon {
      position: absolute;
      top: 50%;
      right: -24px;
      color: @primary-color;
      cursor: pointer;
      transform: translateY(-50%);
    }
  }

  .spec-display {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    &-count {
      height: 16px;
      min-width: 20px;
      font-size: 12px;
      line-height: 16px;
      color: @gray-color;
      text-align: center;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }

  .info-wrapper {
    width: 530px;
    padding: 9px 2px;
    font-size: 12px;
    color: @default-color;

    .info {
      display: flex;
      overflow: hidden;
      line-height: 32px;
      align-items: center;
    }

    .info-name {
      display: inline-block;
      width: 100%;
      padding-bottom: 12px;
    }

    .info-title {
      width: 120px;
      text-align: right;
      flex-shrink: 0;
    }

    .info-value {
      color: @title-color;
      flex: 0 1 100%;
    }
  }
</style>
