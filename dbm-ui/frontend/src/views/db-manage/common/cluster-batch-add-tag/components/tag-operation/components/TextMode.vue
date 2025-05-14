<template>
  <div class="text-mode-main">
    <BkPopover
      always
      placement="top"
      theme="light">
      <template #content>
        <div style="line-height: 20px">
          <div style="font-weight: 700">{{ tipTitle }}</div>
          <div>{{ exampleTip1 }}</div>
          <div>{{ exampleTip2 }}</div>
        </div>
      </template>
      <BkInput
        ref="inputRef"
        v-model="localValue"
        :autosize="{ minRows: 8, maxRows: 20 }"
        :over-max-length-limit="false"
        :placeholder="placeholder"
        :resize="false"
        type="textarea" />
    </BkPopover>
    <div
      v-if="!isVerifyPassed"
      class="error-tip">
      <DbIcon
        style="font-size: 14px"
        type="exclamation-fill" />
      <span class="ml-4">{{ verifyTip }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { tagKeyRegex, tagValueRegex } from '@common/regex';

  import type { KeyValueMapType, TagsPairType } from '../Index.vue';

  interface Props {
    data?: TagsPairType;
    keyValueMap: KeyValueMapType;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => TagsPairType | null;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });

  const { t } = useI18n();

  const inputRef = ref();
  const localValue = ref('');
  const isVerifyPassed = ref(true);
  const verifyTip = ref('');

  const tipTitle = `${t('请按照格式输入标签，如')}：`;
  const exampleTip1 = t('所属部门：技术部门');
  const exampleTip2 = t('负责人：admin');
  const placeholder = `${tipTitle}\n${exampleTip1}\n${exampleTip2}`;

  watch(
    () => props.data,
    () => {
      if (props.data && Object.keys(props.data).length > 0) {
        let tmpStr = '';
        Object.entries(props.data).forEach(([key, item]) => {
          tmpStr += `${key}:${item.label}\n`;
        });
        localValue.value = tmpStr;
      }
    },
    { immediate: true },
  );

  const checkInputValue = () => {
    const pairStrList = localValue.value
      .trim()
      .split(/\n/)
      .filter((item) => !!item);
    const validPairRegex = /[:：/]/;
    const pairInfo: TagsPairType = {};
    const notExistValues: {
      key: string;
      value: string;
    }[] = [];

    for (const pairStr of pairStrList) {
      if (!validPairRegex.test(pairStr)) {
        return null;
      }
      const [key, value] = pairStr.split(validPairRegex);

      if (!key) {
        verifyTip.value = t('键必填');
        return null;
      }

      if (!props.keyValueMap[key]) {
        notExistValues.push({
          key,
          value,
        });
      }

      if (!tagKeyRegex.test(key)) {
        verifyTip.value = t('标签键为1-50个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
        return null;
      }

      if (!value) {
        verifyTip.value = t('值必填');
        return null;
      }

      if (props.keyValueMap[key] && !props.keyValueMap[key].find((item) => item.value === value)) {
        notExistValues.push({
          key,
          value,
        });
      }

      if (!tagValueRegex.test(value)) {
        verifyTip.value = t('标签值为1-100个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
        return null;
      }

      if (props.keyValueMap[key]) {
        Object.assign(pairInfo, {
          [key]: {
            label: value,
            value: props.keyValueMap[key].find((item) => item.value === value)?.id,
          },
        });
      }
    }

    if (notExistValues.length) {
      verifyTip.value = t('标签m不存在', {
        m: notExistValues.map((item) => `${item.key} : ${item.value}`).join(' , '),
      });
      return null;
    }

    return pairInfo;
  };

  onMounted(() => {
    inputRef.value.focus();
  });

  defineExpose<Exposes>({
    getValue() {
      const pairInfo = checkInputValue();
      isVerifyPassed.value = !!pairInfo;
      return pairInfo;
    },
  });
</script>
<style lang="less" scoped>
  .text-mode-main {
    .error-tip {
      margin-top: 8px;
      font-size: 12px;
      color: #ea3636;
    }
  }
</style>
