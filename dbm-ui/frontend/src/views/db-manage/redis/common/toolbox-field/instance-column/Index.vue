<template>
  <EditableColumn
    :append-rules="rules"
    :field="field"
    fixed="left"
    :label="label || t('目标实例')"
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
    <EditableInput
      v-model="modelValue.instance_address"
      :placeholder="t('请输入或选择实例')" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="isShowInstaceSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :selected="selectedList"
    :tab-list-config="tabListConfig"
    @change="handleInstanceSelectChange" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { getRedisInstances } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    afterInput?: (data: RedisInstanceModel) => void;
    field?: string;
    label?: string;
    selected: {
      instance_address: string;
    }[];
    tabListConfig?: Record<string, PanelListType>;
  }

  type Emits = (e: 'batch-edit', value: RedisInstanceModel[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    afterInput: undefined,
    field: 'instance.instance_address',
    label: '',
    tabListConfig: undefined,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof getRedisInstances>['results'][number]>>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('目标实例输入格式有误'),
      trigger: 'change',
      validator: (value: string) => ipPort.test(value),
    },
    {
      message: t('目标实例重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.instance_address === value).length < 2,
    },
    {
      message: t('目标实例不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
  ];

  const isShowInstaceSelector = ref(false);
  const isLoading = ref(false);

  const selectedList = computed(
    () =>
      ({
        [ClusterTypes.REDIS]: props.selected,
      }) as unknown as InstanceSelectorValues<IValue>,
  );

  watch(
    () => modelValue.value.instance_address,
    () => {
      if (!modelValue.value.id && modelValue.value.instance_address) {
        isLoading.value = true;
        modelValue.value.id = undefined;
        getRedisInstances({
          instance_address: modelValue.value.instance_address,
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
      if (!modelValue.value.instance_address) {
        modelValue.value.id = undefined;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowSelector = () => {
    isShowInstaceSelector.value = true;
  };

  const handleInstanceSelectChange = (selected: Record<string, RedisInstanceModel[]>) => {
    const clusterList = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', clusterList);
  };
</script>
