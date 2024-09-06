<template>
  <div class="target-form-item">
    <div class="target-prefix">{{ t('业务') }}</div>
    <BkSelect
      v-model="modelValue"
      class="target-select"
      :class="{
        'is-error': Boolean(errorMessage),
      }"
      :clearable="false"
      :disabled="disabled"
      filterable
      :input-search="false"
      @change="handleChange">
      <BkOption
        v-for="item in bizList"
        :key="item.bk_biz_id"
        :label="item.name"
        :value="item.bk_biz_id" />
    </BkSelect>
    <div
      v-if="errorMessage"
      class="error-icon">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <div class="action-box">
      <DbIcon
        class="action-btn"
        type="plus-fill"
        @click="handleAppend" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/source/cmdb';

  import useValidtor from '@components/render-table/hooks/useValidtor';

  interface Props {
    disabled: boolean;
  }

  interface Emits {
    (e: 'change', value: number): void;
    (e: 'add'): void;
  }

  interface Exposes {
    getValue: () => Promise<number>;
  }

  withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number>({
    default: 0,
  });

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('必须选择业务'),
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  const { data: bizList } = useRequest(getBizs);

  const handleChange = (value: number) => {
    validator(value);
    emits('change', value);
  };

  const handleAppend = () => {
    emits('add');
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(modelValue.value).then(() => Promise.resolve(modelValue.value));
    },
  });
</script>

<style lang="less" scoped>
  .is-error {
    :deep(.bk-input--text) {
      background-color: #fff0f1 !important;
    }
  }
</style>
