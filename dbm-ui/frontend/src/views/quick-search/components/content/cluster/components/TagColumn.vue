<template>
  <BkTableColumn
    field="tags"
    :label="t('标签')"
    :min-width="250">
    <template #default="{ data: rowData }: { data: QuickSearchClusterModel }">
      <template v-if="rowData.tags.length > 0">
        <div
          v-for="tagItem in getList(rowData.tags)"
          :key="tagItem.id">
          <TextHighlight
            high-light-color="#FF9C01"
            :keyword="keyword"
            :text="`${tagItem.key}:${tagItem.value}`" />
        </div>
        <BkButton
          v-if="rowData.tags.length > 3"
          text
          theme="primary"
          @click="handleExpand">
          {{ isExpand ? t('收起') : t('共n个', [rowData.tags.length]) }}
        </BkButton>
      </template>
      <span v-else>--</span>
    </template>
  </BkTableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';

  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    keyword: string;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isExpand = ref(false);

  const getList = (data: QuickSearchClusterModel['tags']) => {
    if (isExpand.value) {
      return data;
    }
    return data.slice(0, 3);
  };

  const handleExpand = () => {
    isExpand.value = !isExpand.value;
  };
</script>

<style lang="less" scoped>
  .redis-cluster-clb {
    color: #8e3aff;
    cursor: pointer;
    background-color: #f2edff;

    &:hover {
      color: #8e3aff;
      background-color: #e3d9fe;
    }
  }

  .redis-cluster-polary {
    color: #3a84ff;
    cursor: pointer;
    background-color: #edf4ff;

    &:hover {
      color: #3a84ff;
      background-color: #e1ecff;
    }
  }
</style>
