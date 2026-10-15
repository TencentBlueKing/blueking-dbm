<template>
  <DbFormItem
    :label="t('部署方案选择')"
    required>
    <BkRadioGroup
      v-model="modelValue"
      :disabled="disabled"
      style="width: 314px"
      @change="handleChange">
      <BkRadioButton
        :label="APPLY_SCHEME.AUTO"
        style="flex: 1">
        {{ t('自动推荐方案') }}
        <DbTag
          size="small"
          theme="success">
          {{ t('实验') }}
        </DbTag>
      </BkRadioButton>
      <BkRadioButton
        :label="APPLY_SCHEME.CUSTOM"
        style="flex: 1">
        {{ t('自定义方案') }}
      </BkRadioButton>
    </BkRadioGroup>
  </DbFormItem>
</template>

<script lang="ts">
  export enum APPLY_SCHEME {
    AUTO = 'auto',
    CUSTOM = 'custom',
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    // 是否只读；由调用方按场景决定，申请页调整申请模式下传 true，工具箱页不传
    disabled?: boolean;
  }

  type Emits = (e: 'change') => void;

  withDefaults(defineProps<Props>(), {
    disabled: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<APPLY_SCHEME>({
    required: true,
  });

  const { t } = useI18n();

  const handleChange = () => {
    emits('change');
  };
</script>
