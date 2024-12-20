<template>
  <EditableTableColumn
    class="edit-spec-column"
    :field="field"
    :label="label"
    required
    :width="300">
    <template
      v-if="labelTip"
      #head>
      <BkPopover
        :content="labelTip"
        placement="top"
        theme="dark">
        <span class="edit-spec-column-label-tip">{{ label }}</span>
      </BkPopover>
    </template>
    <EditSelect v-model="modelValue">
      <SpecPanel
        v-for="(item, index) in specList"
        :key="index"
        :data="item.specData">
        <template #hover>
          <BkOption
            :key="index"
            :label="item.label"
            :value="item.value">
            <div class="edit-spec-column-spec-item">
              <span class="text-overflow">
                {{ item.label }}
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
    </EditSelect>
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { Column as EditableTableColumn, Select as EditSelect } from '@components/editable-table/Index.vue';

  import SpecPanel, { type SpecInfo } from './components/SpecPanel.vue';

  interface Props {
    label: string;
    labelTip?: string;
    field: string;
    clusterType?: string;
    machineType?: string;
    bkCloudId?: number;
    currentSpecIds?: number[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const specList = ref<
    {
      value: number;
      label: string;
      specData: SpecInfo;
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
      if (props.bkCloudId) {
        fetchSpecResourceCount({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: props.bkCloudId,
          spec_ids: specList.value.map((item) => item.specData.id),
        });
      }
    },
  });

  watch(
    () => [props.clusterType, props.machineType],
    () => {
      if (props.clusterType && props.machineType) {
        fetchResourceSpecList({
          spec_cluster_type: props.clusterType,
          spec_machine_type: props.machineType,
          limit: -1,
          offset: 0,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .edit-spec-column-label-tip {
    border-bottom: 1px dashed #979ba5;
  }

  .edit-spec-column-spec-item {
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
