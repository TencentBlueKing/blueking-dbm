<template>
  <div
    class="entry-config-multi"
    :class="{ 'is-error': isError }">
    <BkInput
      v-model.trim="localValue"
      class="input-box"
      :placeholder="t('请输入数值')"
      :rows="rows"
      style="resize: none"
      type="textarea"
      @blur="handleBlur"
      @input="handleInput" />
    <div
      v-show="isError"
      class="error-box">
      <DbIcon
        v-bk-tooltips="t('输入有误')"
        class="error-icon"
        type="exclamation-fill" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Exposes {
    getValue: () => string[];
  }

  const { t } = useI18n();

  const localValue = ref('');
  const isError = ref(false);

  const rows = computed(() => {
    let len = localValue.value.split('\n').length;
    len = len < 4 ? 4 : len;
    return len > 16 ? 16 : len;
  });

  const checkRow = (value: string) => /^[0-9]*$/.test(value);

  const checkInput = () => {
    const inputArr = localValue.value.split('\n');
    const isExistError = inputArr.find((item) => !checkRow(item));
    return !isExistError;
  };

  const handleBlur = () => {
    const isChecked = checkInput();
    isError.value = !isChecked;
  };

  const handleInput = () => {
    isError.value = false;
  };

  defineExpose<Exposes>({
    getValue() {
      const isChecked = checkInput();
      if (isChecked) {
        return localValue.value.split('\n');
      }
      return [];
    },
  });
</script>
<style lang="less" scoped>
  .entry-config-multi {
    position: relative;

    .input-box {
      height: auto;
      max-height: 300px;
      min-height: 84px;
    }

    .error-box {
      position: absolute;
      top: 0;
      right: 0;
      display: flex;
      width: 25px;
      height: 100%;
      padding-top: 12px;
      justify-content: center;
      align-items: center;

      .error-icon {
        font-size: 14px;
        color: #ea3636;
      }
    }
  }

  .is-error {
    :deep(textarea) {
      background-color: #fff0f1;
    }
  }
</style>
