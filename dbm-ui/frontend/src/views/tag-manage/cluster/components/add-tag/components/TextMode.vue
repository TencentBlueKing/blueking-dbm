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
          <div>{{ exampleTip3 }}</div>
        </div>
      </template>
      <BkInput
        v-model="localValue"
        :placeholder="placeholder"
        :resize="false"
        :rows="8"
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

  import type { TagsPairType } from '../Index.vue';

  interface Props {
    data?: TagsPairType;
    existedKeys: Set<string>;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => Record<string, string[]> | null;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const localValue = ref('');
  const isVerifyPassed = ref(true);

  const tipTitle = t('请按照格式输入标签，如：');
  const exampleTip1 = t('所属部门：技术部门｜设计部｜产品部');
  const exampleTip2 = t('产品质量：优秀｜中等｜不及格');
  const exampleTip3 = t('多个标签值以空格、逗号、分号、竖线分割');
  const verifyTip = ref('');
  const placeholder = `${tipTitle}\n${exampleTip1}\n${exampleTip2}\n${exampleTip3}`;

  watch(verifyTip, () => {
    isVerifyPassed.value = !verifyTip.value;
  });

  watch(
    () => props.data,
    () => {
      if (props.data && Object.keys(props.data).length > 0) {
        let tmpStr = '';
        Object.entries(props.data).forEach(([key, value]) => {
          tmpStr += `${key}:${value.join('|')}\n`;
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
    const validPairRegex = /[:：]/;
    const pairInfo: Record<string, string[]> = {};

    for (const pairStr of pairStrList) {
      if (!validPairRegex.test(pairStr)) {
        verifyTip.value = t('格式错误');
        return null;
      }
      const [key, value] = pairStr.split(validPairRegex);
      const valueList = value.trim().split(/[,，;；|｜]/);
      if (!key) {
        verifyTip.value = t('键必填');
        return null;
      }

      if (props.existedKeys.has(key)) {
        verifyTip.value = t('标签键m已存在', { m: key });
        return null;
      }

      if (!tagKeyRegex.test(key)) {
        verifyTip.value = t('标签键为1-50个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
        return null;
      }

      if (!valueList.length) {
        verifyTip.value = t('值必填');
        return null;
      }

      if (valueList.every((item) => !tagValueRegex.test(item))) {
        verifyTip.value = t('标签值为1-100个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
        return null;
      }

      Object.assign(pairInfo, {
        [key]: valueList,
      });
    }

    return pairInfo;
  };

  defineExpose<Exposes>({
    getValue() {
      const pairInfo = checkInputValue();
      return pairInfo;
    },
  });
</script>
<style lang="less" scoped>
  .text-mode-main {
    position: relative;

    .error-tip {
      position: absolute;
      bottom: -18px;
      font-size: 12px;
      color: #ea3636;
    }
  }
</style>
