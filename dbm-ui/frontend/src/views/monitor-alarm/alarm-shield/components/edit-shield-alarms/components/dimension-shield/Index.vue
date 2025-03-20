<template>
  <BkFormItem
    :label="t('屏蔽的维度')"
    property="dimensions"
    required>
    <DimensionSelector
      ref="dimensionSelectorRef"
      :data="data"
      :db-type="dbType"
      :disabled="disabled" />
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import AlarmShieldModel from '@services/model/monitor/alarm-shield';

  import DimensionSelector, {
    type Exposes as DimensionSelectorExpose,
  } from './components/dimension-selector/Index.vue';

  interface Props {
    data?: AlarmShieldModel['dimension_config'];
    dbType?: string;
    disabled?: boolean;
  }

  interface Exposes {
    getValue: () => {
      dimension_config: ReturnType<DimensionSelectorExpose['getValue']>;
    };
  }

  withDefaults(defineProps<Props>(), {
    data: undefined,
    dbType: '',
    disabled: false,
  });

  const { t } = useI18n();

  const dimensionSelectorRef = ref<InstanceType<typeof DimensionSelector>>();

  defineExpose<Exposes>({
    getValue() {
      return {
        dimension_config: dimensionSelectorRef.value!.getValue(),
      };
    },
  });
</script>
