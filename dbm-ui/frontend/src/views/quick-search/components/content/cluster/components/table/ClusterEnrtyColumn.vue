<template>
  <TableColumn
    col-key="cluster_entry"
    :min-width="250"
    :title="t('访问入口')">
    <template #default="{ row: rowData }: { row: QuickSearchClusterModel }">
      <template v-if="rowData.dispalyEntryList.length > 0">
        <div
          v-for="entryItem in getList(rowData.dispalyEntryList)"
          :key="entryItem.entry">
          <TextHighlight
            class="mr-4"
            :filter-type="filterType"
            high-light-color="#FF9C01"
            :keyword="keyword"
            :text="entryItem.entry" />
          <BkTag
            v-if="['clb', 'clbDns'].includes(entryItem.cluster_entry_type)"
            class="redis-cluster-clb"
            size="small">
            CLB
          </BkTag>
          <BkTag
            v-if="entryItem.cluster_entry_type === 'polaris'"
            class="redis-cluster-polary"
            size="small">
            {{ t('北极星') }}
          </BkTag>
          <!-- <BkTag
            v-if="entryItem.role === 'master_entry'"
            size="small"
            theme="info">
            {{ t('主') }}
          </BkTag> -->
          <BkTag
            v-if="entryItem.role === 'slave_entry'"
            size="small"
            theme="success">
            {{ t('从') }}
          </BkTag>
        </div>
        <BkButton
          v-if="rowData.dispalyEntryList.length > 3"
          text
          theme="primary"
          @click="handleExpand">
          {{ isExpand ? t('收起') : t('共n个', [rowData.dispalyEntryList.length]) }}
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

  const isExpand = ref(false);

  const getList = (data: QuickSearchClusterModel['dispalyEntryList']) => {
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
