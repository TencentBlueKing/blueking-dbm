<template>
  <div class="key-value-pair-main">
    <div class="key-input-wraper">
      <BkInput
        v-model="pairInfo.key"
        class="key-input"
        :class="{ 'is-not-valid': !isKeyVerifyPass }"
        @change="checkInputKey" />
      <DbIcon
        v-if="!isKeyVerifyPass"
        v-bk-tooltips="keyVerifyTip"
        class="error-icon"
        type="exclamation-fill" />
    </div>
    <div class="value-input-wraper">
      <BkTagInput
        allow-auto-match
        allow-create
        class="value-input"
        :class="{ 'is-not-valid': !isValueVerifyPass }"
        collapse-tags
        has-delete-icon
        :model-value="pairInfo.value"
        :placeholder="t('请输入标签值（多个标签值以逗号、分号、竖线分割，回车完成输入）')"
        @change="checkInputValue" />
      <DbIcon
        v-if="!isValueVerifyPass"
        v-bk-tooltips="valueVerifyTip"
        class="error-icon"
        style="right: 18px"
        type="exclamation-fill" />
    </div>
    <div class="operation-main">
      <DbIcon
        type="plus-fill"
        @click="handleAdd" />
      <DbIcon
        class="ml-10"
        type="minus-fill"
        @click="handleDelete" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { tagKeyRegex, tagValueRegex } from '@common/regex';

  interface Props {
    data: typeof pairInfo.value;
    existedKeys: Set<string>;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'delete'): void;
  }

  interface Exposes {
    getValue: () => Record<string, string[]> | null;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const pairInfo = ref({
    key: '',
    value: [] as string[],
  });
  const isKeyVerifyPass = ref(true);
  const isValueVerifyPass = ref(true);
  const keyVerifyTip = ref(t('必填'));
  const valueVerifyTip = ref(t('必填'));

  watch(
    () => props.data,
    () => {
      if (props.data.key) {
        pairInfo.value.key = props.data.key;
        pairInfo.value.value = props.data.value;
        keyVerifyTip.value = '';
        valueVerifyTip.value = '';
      }
    },
    { immediate: true },
  );

  watch(keyVerifyTip, () => {
    isKeyVerifyPass.value = !keyVerifyTip.value;
  });

  watch(valueVerifyTip, () => {
    isValueVerifyPass.value = !valueVerifyTip.value;
  });

  const checkInputKey = (key: string) => {
    if (!key) {
      keyVerifyTip.value = t('必填');
      return;
    }

    if (props.existedKeys.has(key)) {
      keyVerifyTip.value = t('标签键已存在');
      return;
    }

    if (!tagKeyRegex.test(key)) {
      keyVerifyTip.value = t('标签键为1-50个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
      return;
    }

    keyVerifyTip.value = '';
  };

  const checkInputValue = (value: string[]) => {
    const inputList = _.flatMap(value.map((item) => item.split(/[\s,，;；|｜]/)));
    pairInfo.value.value = inputList;
    if (!value.length) {
      valueVerifyTip.value = t('必填');
      return;
    }

    if (inputList.some((item) => !tagValueRegex.test(item))) {
      valueVerifyTip.value = t('标签值为1-100个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
      return;
    }

    valueVerifyTip.value = '';
  };

  const handleAdd = () => {
    emits('add');
  };

  const handleDelete = () => {
    emits('delete');
  };

  defineExpose<Exposes>({
    getValue() {
      isKeyVerifyPass.value = !!pairInfo.value.key && !keyVerifyTip.value;
      isValueVerifyPass.value = !!pairInfo.value.value.length && !valueVerifyTip.value;
      if (!isKeyVerifyPass.value || !isValueVerifyPass.value) {
        return null;
      }

      return {
        [pairInfo.value.key]: pairInfo.value.value,
      };
    },
  });
</script>
<style lang="less" scoped>
  .key-value-pair-main {
    display: flex;
    align-items: center;

    .key-input-wraper {
      position: relative;

      .key-input {
        width: 210px;
      }
    }

    .value-input-wraper {
      position: relative;

      .value-input {
        width: 340px;
        margin-right: 8px;
        margin-left: 14px;
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

    .operation-main {
      font-size: 14px;
      color: #979ba5;
      cursor: pointer;
    }

    .is-not-valid {
      :deep(.bk-input--text) {
        background-color: #fff0f1;
      }

      :deep(.bk-tag-input-trigger) {
        background-color: #fff0f1;

        .clear-icon {
          display: none !important;
        }
      }
    }
  }
</style>
