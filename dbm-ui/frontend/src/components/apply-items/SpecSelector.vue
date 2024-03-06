<template>
  <div class="spec-selector-wrapper">
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
          :offset="18"
          placement="right-start"
          :popover-delay="0"
          theme="light">
          <div class="spec-display">
            <span class="text-overflow">{{ item.spec_name }}</span>
            <span
              v-if="typeof item.count === 'number'"
              class="spec-display-count">
              {{ item.count }}
            </span>
          </div>
          <template #content>
            <div class="info-wrapper">
              <strong class="info-name">{{ item.spec_name }}</strong>
              <div
                v-if="typeof item.count === 'number'"
                class="info">
                <span class="info-title">{{ $t('可用主机数') }}：</span>
                <span class="info-value">{{ item.count ?? 0 }}</span>
              </div>
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
                style="align-items: start">
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
                style="align-items: start">
                <span
                  v-overflow-tips="{
                    content: $t('每台主机实例数量'),
                    zIndex: 99999,
                  }"
                  class="info-title text-overflow">{{ $t('每台主机实例数量') }}：</span>
                <span class="info-value">{{ item.instance_num }}</span>
              </div>
            </div>
          </template>
        </BkPopover>
      </BkOption>
    </BkSelect>
    <DbIcon
      v-if="showRefreshIcon"
      v-bk-tooltips="$t('刷新获取最新资源规格')"
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

  interface ResourceSpecData extends ResourceSpecModel {
    count?: number;
  }

  interface Emits {
    (e: 'update:modelValue', value: number | string): void;
  }

  interface Props {
    modelValue: number | string;
    clusterType: string;
    machineType: string;
    bizId: number | string;
    cloudId: number | string;
    showRefresh?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
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
    onSuccess: () => {
      list.value = data.value?.results ?? [];
    },
    onError: () => {
      list.value = [];
    },
  });

  const getData = () => {
    fetchData({
      limit: -1,
      spec_cluster_type: props.clusterType,
      spec_machine_type: props.machineType,
      enable: true,
    });
  };

  watch(
    [() => props.clusterType, () => props.machineType],
    () => {
      if (props.clusterType && props.machineType) {
        getData();
      }
    },
    { immediate: true },
  );

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

  const fetchSpecResourceCount = _.debounce(() => {
    getSpecResourceCount({
      bk_biz_id: Number(props.bizId),
      bk_cloud_id: Number(props.cloudId),
      spec_ids: list.value.map((item) => item.spec_id),
    }).then((data) => {
      list.value = list.value.map((item) => ({
        ...item,
        name: item.spec_name,
        count: data[item.spec_id],
      }));
    });
  }, 100);

  watch(
    [() => props.bizId, () => props.cloudId, data],
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
    { immediate: true, deep: true },
  );

  defineExpose({
    getData() {
      const item = list.value.find((item) => item.spec_id === props.modelValue);
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

  .bk-select-option {
    &.is-selected {
      .spec-display-count {
        color: white;
        background-color: #a3c5fd;
      }
    }
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
