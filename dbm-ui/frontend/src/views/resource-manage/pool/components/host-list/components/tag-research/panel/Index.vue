<template>
  <div class="tag-research-panel">
    <DbIcon
      class="funnel-icon"
      type="funnel" />
    <span>{{ t('标签搜索项：') }}</span>
    <BkTag
      v-for="item in modelValue"
      :key="item.id"
      closable
      @close="() => handleDelete(item)">
      <DbIcon
        class="mr-2"
        type="tag-3" />
      <span>{{ item.value.value }}</span>
    </BkTag>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type ResourceTagModel from '@services/model/db-resource/ResourceTag';

  const { t } = useI18n();

  const modelValue = defineModel<ResourceTagModel[]>({
    default: () => [],
  });

  const handleDelete = (data: ResourceTagModel) => {
    modelValue.value = modelValue.value.filter((item) => item.id !== data.id);
  };
</script>

<style scoped lang="less">
  .tag-research-panel {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 15px;
    font-size: 12px;
    .funnel-icon {
      margin-right: 9.5px;
    }
  }
</style>
