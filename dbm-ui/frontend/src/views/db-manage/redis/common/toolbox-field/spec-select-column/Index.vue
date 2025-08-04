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
      <BkOption
        v-for="(item, index) in specList"
        :key="index"
        :label="item.spec_name"
        :value="item.spec_id">
        <SpecDetailPopover
          :data="item"
          placement="right">
          <div class="spec-select-column-spec-item">
            <span class="text-overflow">
              <slot
                :label="item.spec_name"
                name="label"
                :value="item.spec_id">
                {{ item.spec_name }}
              </slot>
              <BkTag
                v-if="currentSpecIds?.includes(item.spec_id)"
                class="ml-4"
                size="small"
                theme="info">
                {{ t('当前规格') }}
              </BkTag>
            </span>
            <span class="spec-count">
              {{ item.availableCount }}
            </span>
          </div>
        </SpecDetailPopover>
      </BkOption>
    </EditableSelect>
  </EditableColumn>
</template>

<script setup lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  interface Props {
    bkCloudId: number;
    clusterType: string;
    currentSpecIds?: number[];
    field: string;
    label: string;
    labelTip?: string;
    machineType: string;
  }

  const props = defineProps<Props>();

  const slots = defineSlots<{
    head?: (value: { label: string }) => VNode;
    label: (value: { label: string; value: number }) => VNode;
  }>();

  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const specList = ref<({ availableCount: number } & ResourceSpecModel)[]>([]);

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value.forEach((item) => {
        Object.assign(item, {
          cavailableCountount: data[item.spec_id],
        });
      });
    },
  });

  const { run: fetchResourceSpecList } = useRequest(getResourceSpecList, {
    manual: true,
    onSuccess(data) {
      specList.value = data.results.map((item) => Object.assign(item, { availableCount: 0 }));
      if (props.bkCloudId) {
        fetchSpecResourceCount({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: props.bkCloudId,
          spec_ids: specList.value.map((item) => item.spec_id),
        });
      }
    },
  });

  watch(
    () => [props.clusterType, props.machineType],
    () => {
      if (props.clusterType && props.machineType) {
        fetchResourceSpecList({
          limit: -1,
          offset: 0,
          spec_cluster_type: props.clusterType,
          spec_machine_type: props.machineType,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    [modelValue, () => props.currentSpecIds],
    () => {
      if (props.currentSpecIds?.length === 1 && !modelValue.value) {
        [modelValue.value] = props.currentSpecIds;
        return;
      }

      // 如果 modelValue 被设置为 字符串 时，若在规格列表中匹配到对应规格则选中（用于批量录入）
      if (modelValue.value && typeof modelValue.value === 'string') {
        const matchedSpecId = specList.value.filter(
          (item) => item.specData.name === (modelValue.value as unknown as string),
        )?.[0]?.specData.id;
        if (matchedSpecId) {
          modelValue.value = matchedSpecId;
        }
      }
    },
    {
      immediate: true,
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

    .spec-count {
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
