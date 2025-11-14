<template>
  <div class="recommend-architecture mb-24">
    <BkCard
      class="mt-8"
      is-collapse
      :title="t('请描述你的需求：')">
      <Form v-model:recommend-architectrue="recommendArchitectrue" />
    </BkCard>
    <BkCard
      class="mt-16"
      is-collapse
      :title="t('架构对比')">
      <Table :recommend-architectrue="recommendArchitectrue" />
    </BkCard>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import Form from './components/Form.vue';
  import Table from './components/Table.vue';

  const { t } = useI18n();

  const recommendArchitectrue = ref('');
</script>

<style lang="less" scoped>
  .recommend-architecture {
    :deep(.bk-card) {
      border: none;

      &:hover {
        box-shadow: none;
      }

      .bk-card-head {
        border-bottom: none;
        height: 44px;
      }

      .bk-card-head-left {
        padding-left: 42px;

        .bk-card-icon {
          left: 20px;
          color: #313238;
        }

        .title {
          color: #313238;
        }
      }
    }
  }
</style>
