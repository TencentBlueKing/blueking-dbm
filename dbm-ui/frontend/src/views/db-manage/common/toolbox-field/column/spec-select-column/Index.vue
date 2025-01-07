<template>
  <EditableColumn
    class="spec-select-column"
    :field="field"
    :label="label"
    required
    :width="300">
    <template #head>
      <slot
        v-if="slots.head"
        :label="label"
        name="head">
      </slot>
      <BkPopover
        v-else-if="labelTip"
        :content="labelTip"
        placement="top"
        theme="dark">
        <span class="spec-select-column-label-tip">{{ label }}</span>
      </BkPopover>
      <span v-else>{{ label }}</span>
    </template>
    <EditableSelect v-model="modelValue">
      <SpecPanel
        v-for="(item, index) in specList"
        :key="index"
        :data="item.specData">
        <template #hover>
          <BkOption
            :key="index"
            :label="item.label"
            :value="item.value">
            <div class="spec-select-column-spec-item">
              <span class="text-overflow">
                <slot
                  :label="item.label"
                  name="label"
                  :value="item.value">
                  {{ item.label }}
                </slot>
                <BkTag
                  v-if="currentSpecIds?.includes(item.value)"
                  size="small"
                  theme="info">
                  {{ t('当前规格') }}
                </BkTag>
              </span>
              <span class="count">
                {{ item.specData.count }}
              </span>
            </div>
          </BkOption>
        </template>
      </SpecPanel>
    </EditableSelect>
  </EditableColumn>
</template>

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import SpecPanel from './components/SpecPanel.vue';

  interface Props {
    label: string;
    labelTip?: string;
    field: string;
    params: {
      clusterType?: string;
      machineType?: string;
      bkCloudId?: number;
    };
    currentSpecIds?: number[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>();

  const slots = defineSlots<{
    head?: (value: { label: string }) => VNode;
    label?: (value: { value: number; label: string }) => VNode;
  }>();

  const { t } = useI18n();

  const specList = ref<
    {
      value: number;
      label: string;
      specData: ComponentProps<typeof SpecPanel>['data'];
    }[]
  >([]);

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value.forEach((item) => {
        Object.assign(item.specData, {
          count: data[item.specData.id],
        });
      });
    },
  });

  const { run: fetchResourceSpecList } = useRequest(getResourceSpecList, {
    manual: true,
    onSuccess(data) {
      specList.value = data.results.map((item) => ({
        value: item.spec_id,
        label: item.spec_name,
        specData: {
          name: item.spec_name,
          cpu: item.cpu,
          id: item.spec_id,
          mem: item.mem,
          count: 0,
          storage_spec: item.storage_spec,
        },
      }));
      if (props.params.bkCloudId) {
        fetchSpecResourceCount({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: props.params.bkCloudId,
          spec_ids: specList.value.map((item) => item.specData.id),
        });
      }
    },
  });

  watch(
    () => [props.params.clusterType, props.params.machineType],
    () => {
      if (props.params.clusterType && props.params.machineType) {
        fetchResourceSpecList({
          spec_cluster_type: props.params.clusterType,
          spec_machine_type: props.params.machineType,
          limit: -1,
          offset: 0,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.currentSpecIds,
    () => {
      if (props.currentSpecIds?.length === 1 && !modelValue.value) {
        [modelValue.value] = props.currentSpecIds;
      }
    },
  );
</script>

<style lang="less" scoped>
  .spec-select-column-label-tip {
    border-bottom: 1px dashed #979ba5;
  }

  .spec-select-column-spec-item {
    display: flex;
    width: 100%;
    flex: 1;
    align-items: center;
    justify-content: space-between;

    .count {
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
</style>
