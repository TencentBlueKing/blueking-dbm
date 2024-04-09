<template>
  <span
    v-if="keywordMatch"
    class="highlight-text">
    <span>{{ keywordMatch[1] || '' }}</span>
    <span :style="{ color: highLightColor }">{{ keywordMatch[2] }}</span>
    <span>{{ keywordMatch[3] || '' }}</span>
  </span>
  <span v-else>
    {{ props.text }}
  </span>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import { batchSplitRegex } from '@common/regex';

  import { encodeRegexp } from '@utils';

  interface Props {
    keyWord: string;
    text: string;
    highLightColor?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    highLightColor: '#3A84FF',
  });

  const keywordMatch = computed(() => {
    const keyWordList = props.keyWord.split(batchSplitRegex);
    for (let i = 0; i < keyWordList.length; i++) {
      const keyWordItem = keyWordList[i];
      const matchResult = props.text.match(new RegExp(`^(.*?)(${encodeRegexp(keyWordItem)})(.*)$`));
      if (matchResult) {
        return matchResult;
      }
    }
    return [];
  });
</script>

<style lang="less" scoped>
  .highlight-text > span {
    display: inline;
  }
</style>
