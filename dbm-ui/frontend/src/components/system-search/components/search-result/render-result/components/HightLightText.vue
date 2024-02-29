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

  import { encodeRegexp } from '@utils';

  interface Props {
    keyWord: string;
    text: string;
    highLightColor?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    highLightColor: '#3A84FF',
  });

  const keywordMatch = computed(() => props.text.match(new RegExp(`^(.*?)(${encodeRegexp(props.keyWord)})(.*)$`)));
</script>

<style lang="less" scoped>
  .highlight-text > span {
    display: inline;
  }
</style>
