<template>
  <EditableTableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="host.ip"
    :label="label"
    :loading="isLoading"
    :min-width="300"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditInput
      v-model="modelValue"
      :disabled="disabled"
      :placeholder="placeholder">
    </EditInput>
    <InstanceSelector
      v-model:is-show="isShowSelector"
      :cluster-types="['mongoCluster']"
      :selected="selected"
      :tab-list-config="tabListConfig"
      @change="handleInstanceSelectChange" />
  </EditableTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getMongoInstancesList } from '@services/source/mongodb';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import { Column as EditableTableColumn, Input as EditInput } from '@components/editable-table/Index.vue';
  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    label: string;
    tabListConfig: Record<ClusterTypes, PanelListType>;
    selected: InstanceSelectorValues<IValue>;
    disabled?: boolean;
    placeholder?: string;
  }

  interface Emits {
    (e: 'batch-edit', value: IValue[]): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => ipv4.test(value),
      trigger: 'change',
      message: t('目标主机输入格式有误'),
    },
    {
      validator: async (value: string) => {
        isLoading.value = true;
        return getMongoInstancesList({
          instance_address: value,
        })
          .then((instance) => instance.results.length > 0)
          .finally(() => {
            isLoading.value = false;
          });
      },
      trigger: 'change',
      message: t('目标主机不存在'),
    },
  ];

  const isShowSelector = ref(false);
  const isLoading = ref(false);

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', data.mongoCluster);
  };
</script>

<style lang="less" scoped>
  .host-selector-btn {
    width: 24px;
    font-size: 16px;
    border: none;
    border-radius: 2px;

    &:hover {
      color: #3a84ff;
      background: #f0f1f5;
    }
  }
</style>
