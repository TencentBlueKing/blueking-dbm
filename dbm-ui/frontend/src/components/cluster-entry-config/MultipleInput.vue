<template>
  <div
    class="entry-config-multi"
    :class="{'is-error': isError}">
    <BkInput
      v-model="modelValue"
      :disabled="disabled"
      placeholder=" "
      :rows="rows"
      style="resize:none;"
      type="textarea"
      @blur="handleBlur"
      @input="handleInput" />
    <div
      v-show="isError"
      class="error-box">
      <div
        v-for="(item, index) in ErrorList"
        :key="index"
        class="tip-box">
        <DbIcon
          v-if="!item.isChecked"
          v-bk-tooltips="item.tip"
          class="error-icon"
          type="exclamation-fill" />
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  import { ipv4 } from '@common/regex';
  export const checkIp = (value: string) => Boolean(value) && ipv4.test(value);
</script>
<script setup lang="ts">


  import { t } from '@locales/index';

  interface Props {
    disabled?: boolean,
  }

  defineProps<Props>();

  const modelValue =  defineModel<string>({
    default: '',
  });

  const isError = ref(false);
  const ErrorList = ref<{isChecked: boolean, tip: string}[]>([]);

  const rows = computed(() => modelValue.value.split('\n').length);

  const handleBlur = () => {
    const inputArr = modelValue.value.split('\n');
    const resultArr = inputArr.map((item) => {
      const isChecked = checkIp(item);
      return {
        isChecked,
        tip: !isChecked && item === '' ? t('IP 不能为空') : t('IP 输入有误'),
      };
    });
    ErrorList.value = resultArr;
    isError.value = resultArr.some(item => !item.isChecked);
  };

  const handleInput = () => {
    isError.value = false;
  };
</script>
<style lang="less" scoped>
.entry-config-multi {
  position: relative;

  .bk-textarea {
    border-radius: 0;
  }

  :deep(textarea) {
    min-height: 42px !important;
    padding: 12px 18px;
    border-radius: 0;
  }

  .error-box {
    position: absolute;
    top: 0;
    right: 0;
    width: 25px;
    height: 100%;
    padding-top: 12px;

    .tip-box {
      display: flex;
      height: 18px;
      padding-top: 3.5px;
      justify-content: center;

      .error-icon {
        font-size: 14px;
        color: #ea3636;
      }
    }

  }
}

.is-error{
  :deep(textarea) {
    background-color: #fff0f1;
  }
}
</style>
