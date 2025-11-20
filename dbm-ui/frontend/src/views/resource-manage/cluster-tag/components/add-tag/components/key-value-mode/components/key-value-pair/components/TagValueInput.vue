<template>
  <div class="tag-value-input-main">
    <BkTagInput
      allow-auto-match
      allow-create
      class="value-input"
      :class="{ 'is-not-valid': !isValueVerifyPass }"
      has-delete-icon
      :model-value="modelValue"
      :placeholder="t('请输入标签值（多个标签值以逗号、分号、竖线分割，回车完成输入）')"
      @change="checkInputValue" />
    <DbIcon
      v-if="!isValueVerifyPass"
      v-bk-tooltips="valueVerifyTip"
      class="error-icon"
      style="right: 18px"
      type="exclamation-fill" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { tagValueRegex } from '@common/regex';

  interface Exposes {
    getValue: () => string[] | null;
  }

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const isValueVerifyPass = ref(true);
  const valueVerifyTip = ref('');

  watch(valueVerifyTip, () => {
    isValueVerifyPass.value = !valueVerifyTip.value;
  });

  const checkInputValue = (value: string[]) => {
    if (!value.length) {
      valueVerifyTip.value = t('必填');
      return;
    }

    const inputList = _.flatMap(value.map((item) => item.split(/[,，;；|｜]/))).filter((item) => !!item.trim());
    modelValue.value = inputList;

    const inputValueMap: Record<string, boolean> = {};
    for (const item of inputList) {
      if (inputValueMap[item]) {
        valueVerifyTip.value = t('标签值不能重复');
        return;
      }
      inputValueMap[item] = true;
    }

    if (inputList.some((item) => !tagValueRegex.test(item))) {
      valueVerifyTip.value = t('标签值为1-100个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
      return;
    }

    valueVerifyTip.value = '';
  };

  defineExpose<Exposes>({
    getValue() {
      checkInputValue(modelValue.value);
      isValueVerifyPass.value = !!modelValue.value.length && !valueVerifyTip.value;
      if (!isValueVerifyPass.value) {
        return null;
      }

      return modelValue.value;
    },
  });
</script>
<style lang="less" scoped>
  .tag-value-input-main {
    position: relative;

    .is-not-valid {
      :deep(.bk-tag-input-trigger) {
        border-color: #ea3636;

        .clear-icon {
          display: none !important;
        }
      }
    }

    .error-icon {
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      font-size: 14px;
      color: #ea3636;
    }
  }
</style>
