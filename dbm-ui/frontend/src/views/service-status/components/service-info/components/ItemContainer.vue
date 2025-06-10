<template>
  <DbCard
    class="service-info-item-container"
    mode="collapse"
    :title="title">
    <template #desc>
      <BkPopover theme="light">
        (
        <span class="normal-count">{{ normalCount }}</span>
        /
        <span class="abnormal-count">{{ abnormalCount }}</span>
        )
        <template #content>
          <span>{{ t('正常') }}: </span>
          <span>{{ normalCount }}</span>
          <span class="ml-12">{{ t('异常') }}: </span>
          <span>{{ abnormalCount }}</span>
        </template>
      </BkPopover>
    </template>
    <slot />
  </DbCard>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      status: string;
    }[];
    title: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const normalCount = computed(() => props.data.filter((item) => item.status === 'running').length);
  const abnormalCount = computed(() => props.data.filter((item) => item.status !== 'running').length);
</script>

<style lang="css" scoped>
  .service-info-item-container {
    .normal-count {
      font-weight: bolder;
      color: #2caf5e;
    }

    .abnormal-count {
      font-weight: bolder;
      color: #ea3636;
    }
  }
</style>
