<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="host.ip"
    :label="label"
    :loading="isLoading"
    :min-width="300"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select-button"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.ip"
      :disabled="disabled"
      :placeholder="placeholder">
    </EditableInput>
    <InstanceSelector
      v-model:is-show="isShowSelector"
      :cluster-types="['mongoCluster']"
      :selected="selected"
      :tab-list-config="tabListConfig"
      @change="handleInstanceSelectChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getMongoInstancesList } from '@services/source/mongodb';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    disabled?: boolean;
    label: string;
    placeholder?: string;
    selected: InstanceSelectorValues<IValue>;
    tabListConfig: Record<ClusterTypes, PanelListType>;
  }

  type Emits = (e: 'batch-edit', value: IValue[]) => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    id?: number;
    ip?: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('目标主机输入格式有误'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
  ];

  const isShowSelector = ref(false);

  const { loading: isLoading, run: runGetMongoInstancesList } = useRequest(getMongoInstancesList, {
    manual: true,
    onSuccess(data) {
      if (data.results.length > 0) {
        [modelValue.value] = data.results;
      }
    },
  });

  watch(
    () => modelValue.value.ip,
    () => {
      if (!modelValue.value.id && modelValue.value.ip) {
        modelValue.value.id = undefined;
        runGetMongoInstancesList({
          extra: 1,
          instance_address: modelValue.value.ip,
        });
      }
      if (!modelValue.value.ip) {
        modelValue.value.id = undefined;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', data.mongoCluster);
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
