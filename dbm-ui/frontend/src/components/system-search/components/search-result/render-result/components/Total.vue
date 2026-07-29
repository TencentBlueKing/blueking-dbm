<template>
  <div
    v-if="isCountShow"
    class="result-count">
    <span> ... {{ t('共 n 条', { n: count }) }} </span>
    <template v-if="!isResultPage">
      ，
      <BkButton
        text
        theme="primary"
        @click="handleToResult">
        {{ t('查看全部') }}
      </BkButton>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    count: number;
  }

  type Emits = (e: 'to-result') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();

  const isCountShow = computed(() => props.count > 10);
  const isResultPage = computed(() => route.name === 'QuickSearch');

  const handleToResult = () => {
    emits('to-result');
  };
</script>

<style lang="less" scoped>
  .result-count {
    height: 32px;
    padding: 0 12px;
    line-height: 32px;
    color: #c4c6cc;
  }
</style>
