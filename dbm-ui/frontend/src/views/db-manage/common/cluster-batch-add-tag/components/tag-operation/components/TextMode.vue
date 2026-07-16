<template>
  <div class="text-mode-main">
    <BkInput
      ref="inputRef"
      v-model="localValue"
      :autosize="{ minRows: 8, maxRows: 20 }"
      :over-max-length-limit="false"
      :placeholder="placeholder"
      :resize="false"
      type="textarea"
      @blur="handleBlurTextarea" />
    <div
      v-if="errorTipList.length > 0"
      class="error-tip">
      <div
        v-for="item in errorTipList"
        :key="item.line"
        class="error-tip-item">
        <DbIcon
          style="font-size: 18px"
          type="close" />
        <span class="ml-4">{{ t('第 n 行', { n: item.line }) }}</span>
        <span class="mr-4">:</span>
        <span class="ml-4">{{ item.tip }}</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { KeyValueMapType, TagsPairType } from '../Index.vue';

  interface Props {
    data?: TagsPairType[];
    keyValueMap: KeyValueMapType;
  }

  interface Exposes {
    getValue: (isIgnoreVerify?: boolean) => TagsPairType[] | null;
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const inputRef = ref();
  const localValue = ref('');
  const errorTipList = ref<
    {
      line: number;
      tip: string;
    }[]
  >([]);

  const placeholder = `${t('请按照格式输入标签，如')}：\n${t('所属部门：技术部门')}\n${t('负责人：admin')}`;

  watch(
    () => props.data,
    () => {
      if (props.data && props.data.length > 0) {
        let tmpStr = '';
        props.data.forEach((item) => {
          tmpStr += `${item.key}:${item.value}\n`;
        });
        localValue.value = tmpStr.trim();
      }
    },
    { immediate: true },
  );

  const checkInputValue = (isIgnoreVerify = false) => {
    errorTipList.value = [];
    const pairStrList = localValue.value.trim().split(/\n/);
    const validPairRegex = /[:：/]/;
    const pairInfo: TagsPairType[] = [];

    for (let i = 0; i < pairStrList.length; i++) {
      const pairStr = pairStrList[i];
      if (!pairStr.trim()) {
        continue;
      }

      if (!validPairRegex.test(pairStr)) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('缺少 : 分隔符'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key: pairStr,
            value: '',
          });
        }
        continue;
      }
      const [key, value] = pairStr.split(validPairRegex);

      if (!key) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('请输入标签键'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key: '',
            value,
          });
        }
        continue;
      }

      if (key.length > 50) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('标签键长度不能超过 50 个字符'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key,
            value,
          });
        }
        continue;
      }

      // 支持中文、字母、数字、连字符、下划线、点号
      if (!/^[\u4e00-\u9fa5a-zA-Z0-9\-_.]+$/.test(key)) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('标签键包含不支持的字符'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key,
            value,
          });
        }
        continue;
      }

      if (!value) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('请输入标签值'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key,
            value: '',
          });
        }
        continue;
      }

      if (value.length > 50) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('标签值长度不能超过 50 个字符'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key,
            value,
          });
        }
        continue;
      }

      // 支持中文、字母、数字、连字符、下划线、点号
      if (!/^[\u4e00-\u9fa5a-zA-Z0-9\-_.]+$/.test(value)) {
        errorTipList.value.push({
          line: i + 1,
          tip: t('标签值包含不支持的字符'),
        });
        if (isIgnoreVerify) {
          pairInfo.push({
            key,
            value,
          });
        }
        continue;
      }

      // 新增键或值
      if (!props.keyValueMap[key]) {
        pairInfo.push({
          key,
          value,
        });
      } else {
        pairInfo.push({
          key,
          value,
        });
      }
    }
    if (errorTipList.value.length && !isIgnoreVerify) {
      return null;
    }

    return pairInfo;
  };

  // 自动 trim：前后空白符、冒号左右空白符均自动清理。如 `  k : v  ` 自动规范为 `k:v`
  const handleBlurTextarea = () => {
    const pairStrList = localValue.value.trim().split(/\n/);
    const validPairRegex = /[:：/]/;
    let tmpStr = '';
    pairStrList.forEach((item) => {
      const [key, value] = item.split(validPairRegex);
      tmpStr += `${key.trim()}:${value.trim()}\n`;
    });
    localValue.value = tmpStr.trim();
    emit('change');
  };

  onMounted(() => {
    inputRef.value.focus();
  });

  defineExpose<Exposes>({
    getValue(isIgnoreVerify = false) {
      const pairInfo = checkInputValue(isIgnoreVerify);
      return pairInfo;
    },
  });
</script>
<style lang="less" scoped>
  .text-mode-main {
    .error-tip {
      max-height: 200px;
      margin-top: 12px;
      overflow-y: auto;
      font-size: 12px;
      color: #ea3636;

      .error-tip-item {
        display: flex;
        align-items: center;
        height: 20px;
      }
    }
  }
</style>
