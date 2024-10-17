<template>
  <div
    v-if="message.length > 0"
    class="cluster-authorize-error">
    <div class="error-title">
      <DbIcon type="attention-fill" />
      <strong>{{ t('提交失败_信息校验不通过_失败具体原因如下') }}</strong>
    </div>
    <p
      v-for="(text, index) of message.split('\n')"
      :key="index"
      class="pl-24">
      {{ text }}
    </p>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    message: string;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .cluster-authorize-error {
    position: sticky;
    top: 0;
    z-index: 10;
    padding: 8px;
    margin: 28px 40px 0;
    font-size: @font-size-mini;
    background: #ffeded;
    border: 1px solid #ffd2d2;
    border-radius: 2px;

    .error-title {
      padding-bottom: 8px;
      color: @danger-color;

      i > {
        margin-right: 8px;
        font-size: @font-size-large;
      }
    }
  }
</style>
