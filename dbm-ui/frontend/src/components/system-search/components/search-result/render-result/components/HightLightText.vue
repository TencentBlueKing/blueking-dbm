<template>
  <span v-if="keywordMatch">
    <span>{{ keywordMatch[1] || '' }}</span>
    <span style="color: #3A84FF">{{ keywordMatch[2] }}</span>
    <span>{{ keywordMatch[3] || '' }}</span>
  </span>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import { encodeRegexp } from '@utils';

  interface Props {
    keyWord: string,
    text: string
  }

  const props = defineProps<Props>();

  const keywordMatch = computed(() => props.text.match(new RegExp(`^(.*?)(${encodeRegexp(props.keyWord)})(.*)$`)));
</script>

