<template>
  <BkSelect
    v-model="modelValue"
    class="tag-research-selector"
    filterable
    multiple
    selected-style="checkbox">
    <template #trigger>
      <BkButton class="trigger-btn">
        <DbIcon
          class="mr-6"
          type="tag-3" />
        {{ t('标签搜索') }}
      </BkButton>
    </template>
    <BkOption
      v-for="item in tagList"
      :key="item.id"
      :label="item.name"
      :value="item" />
  </BkSelect>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceTagModel from '@services/model/db-resource/ResourceTag';
  import { listTag } from '@services/source/tag';

  const modelValue = defineModel<ResourceTagModel[]>({
    default: [],
  });

  const { t } = useI18n();

  const tagList = ref<
    Array<{
      id: number;
      name: string;
      value: ResourceTagModel;
    }>
  >([]);

  useRequest(listTag, {
    onSuccess(data) {
      tagList.value = data.results.map((item) => ({
        id: item.id,
        name: item.value,
        value: item,
      }));
    },
  });
</script>

<style scoped lang="less">
  .tag-research-selector {
    width: 150;
    .trigger-btn {
      margin-left: 8px;
      width: 150px;
    }
  }
</style>
