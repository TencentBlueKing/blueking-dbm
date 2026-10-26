<template>
  <TableColumn
    col-key="tags"
    :min-width="250"
    :title="t('标签')">
    <template #default="{ row: rowData }: { row: QuickSearchClusterModel }">
      <template v-if="rowData.tags.length > 0">
        <div
          v-for="tagItem in getList(rowData.id, rowData.tags)"
          :key="tagItem.id">
          <TextHighlight
            :filter-type="filterType"
            high-light-color="#FF9C01"
            :keyword="keyword"
            :text="`${tagItem.key}:${tagItem.value}`" />
        </div>
        <BkButton
          v-if="rowData.tags.length > 3"
          text
          theme="primary"
          @click="handleExpand(rowData.id)">
          {{ expandedIds.has(rowData.id) ? t('收起') : t('共n个', [rowData.tags.length]) }}
        </BkButton>
      </template>
      <span v-else>--</span>
    </template>
  </TableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';

  import { FilterType } from '@common/const';

  import TextHighlight from '@components/text-highlight/Index.vue';

  interface Props {
    filterType: FilterType;
    keyword: string;
  }

  defineProps<Props>();

  const { t } = useI18n();

  // 展开状态按行记录，整列共用一个开关会让所有行一起展开
  const expandedIds = ref(new Set<number>());

  const getList = (id: number, data: QuickSearchClusterModel['tags']) => {
    if (expandedIds.value.has(id)) {
      return data;
    }
    return data.slice(0, 3);
  };

  const handleExpand = (id: number) => {
    const ids = new Set(expandedIds.value);
    if (ids.has(id)) {
      ids.delete(id);
    } else {
      ids.add(id);
    }
    expandedIds.value = ids;
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
