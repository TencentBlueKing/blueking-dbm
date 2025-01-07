<template>
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="host.ip"
    fixed="left"
    :label="label"
    :loading="isLoading"
    :min-width="240"
    required>
    <template #headAppend>
      <BkButton
        text
        theme="primary"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </BkButton>
    </template>
    <EditableInput
      v-model="modelValue.ip"
      :disabled="disabled"
      :placeholder="placeholder">
    </EditableInput>
    <InstanceSelector
      v-model:is-show="isShowSelector"
      :cluster-types="clusterTypes"
      :selected="selected"
      :tab-list-config="tabListConfig"
      @change="handleInstanceSelectChange" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisMachineModel from '@services/model/redis/redis-machine';
  import { getRedisMachineList } from '@services/source/redis';

  import { ipv4 } from '@common/regex';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';

  type InstanceSelectorProps = ComponentProps<typeof InstanceSelector>;

  interface Props {
    label: string;
    clusterTypes: InstanceSelectorProps['clusterTypes'];
    selected: InstanceSelectorValues<IValue>;
    tabListConfig?: InstanceSelectorProps['tabListConfig'];
    disabled?: boolean;
    placeholder?: string;
    afterInput?: (data: RedisMachineModel) => void;
  }

  interface Emits {
    (e: 'batch-edit', value: IValue[]): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_host_id: number;
    ip: string;
  }>({
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
      validator: () => Boolean(modelValue.value.bk_host_id),
      trigger: 'change',
      message: t('目标主机不存在'),
    },
  ];

  const isShowSelector = ref(false);
  const isLoading = ref(false);

  watch(
    () => modelValue.value.ip,
    () => {
      if (!modelValue.value.bk_host_id && modelValue.value.ip) {
        isLoading.value = true;
        modelValue.value.bk_host_id = 0;
        getRedisMachineList({
          ip: modelValue.value.ip,
        })
          .then((data) => {
            if (data.results.length > 0) {
              if (props.afterInput) {
                props.afterInput(data.results[0]);
              } else {
                [modelValue.value] = data.results;
              }
            }
          })
          .finally(() => {
            isLoading.value = false;
          });
      }
      if (!modelValue.value.ip) {
        modelValue.value.bk_host_id = 0;
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
    const hostList = Object.values(data).flatMap((selectedList) => selectedList);
    emits('batch-edit', hostList);
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
