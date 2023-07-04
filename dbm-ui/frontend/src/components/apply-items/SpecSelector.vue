<template>
  <BkSelect
    class="spec-selector"
    :loading="loading"
    :model-value="modelValue"
    @change="handleChange">
    <BkOption
      v-for="item in list"
      :key="item.spec_id"
      :label="item.spec_name"
      :value="item.spec_id">
      <BkPopover
        placement="right-start"
        theme="light">
        <div>{{ item.spec_name }}</div>
        <template #content>
          <div class="info-wrapper">
            <strong class="info-name">{{ item.spec_name }}</strong>
            <div class="info">
              <span class="info-title">CPU：</span>
              <span class="info-value">({{ item.cpu.min }} ~ {{ item.cpu.max }}) {{ $t('核') }}</span>
            </div>
            <div class="info">
              <span class="info-title">{{ $t('内存') }}：</span>
              <span class="info-value">({{ item.mem.min }} ~ {{ item.mem.max }}) G</span>
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
                  :data="item.storage_spec" />
              </span>
            </div>
            <div
              v-if="item.instance_num"
              class="info"
              style="align-items: start;">
              <span
                v-overflow-tips="{
                  content: $t('每台主机实例数量'),
                  zIndex: 99999
                }"
                class="info-title text-overflow">{{ $t('每台主机实例数量') }}：</span>
              <span class="info-value">{{ item.instance_num }}</span>
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

  import { getResourceSpecList } from '@services/resourceSpec';

  interface Emits {
    (e: 'update:modelValue', value: number | string): void
  }

  interface Props {
    modelValue: number | string,
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
  } = useRequest(getResourceSpecList, {
    manual: true,
  });

  const list = computed(() => data.value?.results || []);

  watch([() => props.clusterType, () => props.machineType], () => {
    if (props.clusterType && props.machineType) {
      fetchData({
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
    emits('update:modelValue', value);
  };

  defineExpose({
    getData() {
      const item = list.value.find(item => item.spec_id === props.modelValue);
      if (item) {
        const { instance_num: instanceNum } = item;
        return {
          spec_name: item.spec_name,
          cpu: item.cpu,
          mem: item.mem,
          storage_spec: item.storage_spec,
          instance_num: instanceNum && instanceNum > 0 ? instanceNum : undefined,
        };
      }
      return {};
    },
  });
</script>

<style lang="less" scoped>
.spec-selector {
  // width: 435px;
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
    width: 120px;
    text-align: right;
    flex-shrink: 0;
  }

  .info-value {
    color: @title-color;
  }
}
</style>
