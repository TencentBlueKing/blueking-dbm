<template>
  <BkSelect
    class="plan-selector"
    :loading="loading"
    :model-value="modelValue.resource_plan_id"
    @change="handleChange">
    <BkOption
      v-for="item in list"
      :key="item.id"
      :label="item.name"
      :value="item.id">
      <BkPopover
        placement="right-start"
        :popover-delay="0"
        theme="light">
        <div>{{ item.name }}</div>
        <template #content>
          <div
            v-if="specMap[item.spec]"
            class="info-wrapper">
            <strong class="info-name">{{ $t('后端存储资源规格') }}</strong>
            <div class="info">
              <span class="info-title">{{ $t('规格名称') }}：</span>
              <span class="info-value">{{ specMap[item.spec].spec_name }}</span>
            </div>
            <div class="info">
              <span class="info-title">{{ $t('机器组数') }}：</span>
              <span class="info-value">{{ item.machine_pair_cnt }}</span>
            </div>
            <div class="info">
              <span class="info-title">CPU：</span>
              <span class="info-value">
                ({{ specMap[item.spec].cpu.min }} ~ {{ specMap[item.spec].cpu.max }}) {{ $t('核') }}
              </span>
            </div>
            <div class="info">
              <span class="info-title">{{ $t('内存') }}：</span>
              <span class="info-value">({{ specMap[item.spec].mem.min }} ~ {{ specMap[item.spec].mem.max }}) G</span>
            </div>
            <div
              class="info"
              style="align-items: start;">
              <span class="info-title">{{ $t('磁盘') }}：</span>
              <span class="info-value">
                <DbOriginalTable
                  :border="['row', 'col', 'outer']"
                  class="custom-edit-table mt-8"
                  :columns="columns"
                  :data="specMap[item.spec].storage_spec" />
              </span>
            </div>
          </div>
        </template>
      </BkPopover>
    </BkOption>
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeployPlan } from '@services/dbResource';
  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { getResourceSpecList } from '@services/resourceSpec';

  interface Values {
    resource_plan_name: string,
    resource_plan_id: number | string,
  }

  interface Emits {
    (e: 'update:modelValue', value: Values): void
  }

  interface Props {
    modelValue: Values,
    clusterType: string,
    machineType: string,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const {
    data,
    loading,
    run: fetchData,
  } = useRequest(fetchDeployPlan, {
    manual: true,
  });

  const {
    data: specData,
    run: fetchSpecData,
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  const list = computed(() => data.value?.results || []);
  const specMap = computed(() => {
    const result: Record<number, ResourceSpecModel> = {};
    (specData.value?.results || []).forEach((item) => {
      result[item.spec_id] = item;
    });
    return result;
  });

  watch([() => props.clusterType, () => props.machineType], (
    [clusterType, machineType],
    [oldClusterType],
  ) => {
    if (clusterType && clusterType !== oldClusterType) {
      fetchData({
        limit: -1,
        offset: 0,
        cluster_type: props.clusterType,
      });
    }
    if (clusterType && machineType) {
      fetchSpecData({
        limit: -1,
        spec_cluster_type: props.clusterType,
        spec_machine_type: props.machineType,
      });
    }
  }, { immediate: true });

  const columns = [
    {
      field: 'mount_point',
      label: t('挂载点'),
    },
    {
      field: 'size',
      label: t('最小容量G'),
    },
    {
      field: 'type',
      label: t('磁盘类型'),
    },
  ];

  const handleChange = (value: number | string) => {
    emits('update:modelValue', {
      resource_plan_id: value,
      resource_plan_name: list.value.find(item => item.id === value)?.name || '',
    });
  };
</script>

<style lang="less" scoped>
.plan-selector {
  width: 462px;
}

.info-wrapper {
  width: 530px;
  padding: 9px 2px;
  font-size: 12px;
  color: @default-color;

  .info {
    display: flex;
    align-items: center;
    line-height: 32px;
  }

  .info-name {
    display: inline-block;
    padding-bottom: 12px;
  }

  .info-title {
    width: 80px;
    text-align: right;
    flex-shrink: 0;
  }

  .info-value {
    color: @title-color;
  }
}
</style>
