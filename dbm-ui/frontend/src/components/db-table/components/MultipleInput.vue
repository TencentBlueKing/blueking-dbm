<template>
  <div class="t-input__wrap">
    <BkInput
      ref="input"
      v-model="localValue"
      :autosize="{
        minRows: 3,
        maxRows: 100,
      }"
      clearable
      :resize="false"
      type="textarea"
      @input="handleInput" />
    <div
      class="mt-4"
      style="line-height: 22px">
      <span>{{ t('支持输入多个值， ”Enter“ 换行') }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    value?: string;
  }
  type Emits = (e: 'change', value: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const inputRef = useTemplateRef('input');
  const localValue = ref('');

  let isInnerSelfChange = false;
  watch(
    () => props.value,
    () => {
      if (isInnerSelfChange) {
        isInnerSelfChange = false;
        return;
      }
      if (!props.value) {
        localValue.value = '';
        return;
      }
      localValue.value = props.value.split(',').join('\n');
    },
    {
      immediate: true,
    },
  );

  const handleInput = (value: string) => {
    isInnerSelfChange = true;
    emits('change', _.uniq(_.filter(value.split(/[ \r\n\t,，;；|｜]/g), (item) => Boolean(_.trim(item)))).join(','));
  };

  onMounted(() => {
    setTimeout(() => {
      inputRef.value?.focus();
    }, 100);
  });
</script>
