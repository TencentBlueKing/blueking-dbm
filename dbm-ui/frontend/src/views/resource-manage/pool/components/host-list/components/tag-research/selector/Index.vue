<template>
  <BkSelect
    v-model="modelValue"
    class="tag-research-selector"
    filterable
    multiple
    :scroll-height="200"
    :scroll-loading="isFetchingTagsList"
    selected-style="checkbox"
    @scroll-end="loadMore">
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
    default: () => [],
  });

  const { t } = useI18n();

  const tagList = ref<
    {
      id: number;
      name: string;
      value: ResourceTagModel;
    }[]
  >([]);
  const pagination = reactive({
    offset: 0,
    limit: 10,
    count: 0,
  });

  const { run: runList, loading: isFetchingTagsList } = useRequest(listTag, {
    manual: true,
    onSuccess(data) {
      pagination.count = data.count;
      tagList.value.push(
        ...data.results.map((item) => ({
          id: item.id,
          name: item.value,
          value: item,
        })),
      );
    },
  });

  const loadMore = () => {
    if (isFetchingTagsList.value) {
      return;
    }

    if (tagList.value.length >= pagination.count) {
      return;
    }
    pagination.offset += pagination.limit;
    runList(pagination);
  };

  onMounted(() => {
    runList(pagination);
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
