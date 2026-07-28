<template>
  <div>
    <Item
      v-for="item in displayDbList"
      :key="item"
      ref="item"
      :biz-id-name-map="bizIdNameMap"
      :db-type="item"
      :form-data="formData"
      :keyword="keyword"
      @clear-search="handleClearSearch" />
    <div v-if="isEmpty">
      <EmptyStatus
        class="quick-search-empty"
        :is-anomalies="false"
        :is-searching="false" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';

  import { DBTypeInfos, FilterType } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import Item from './components/Item.vue';

  interface Props {
    bizIdNameMap: Record<number, string>;
    formData: {
      bk_biz_ids: number[];
      db_types: string[];
      filter_type: FilterType;
      resource_types: string[];
    };
    keyword: string;
  }

  type Emits = (e: 'clear-search') => void;

  interface Exposed {
    fetchData: () => void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const itemRefs = useTemplateRef<Array<InstanceType<typeof Item>>>('item');

  // name 需按字母序排序
  const dbList = _.sortBy(Object.values(DBTypeInfos), 'name').map((item) => item.id);

  const displayDbList = computed(() => {
    const dbTypes = props.formData.db_types;
    if (dbTypes.length > 0) {
      return dbList.filter((item) => props.formData.db_types.includes(item));
    }
    return dbList;
  });
  const isEmpty = computed(() => {
    return itemRefs.value?.every((item) => item.getCount() === 0);
  });

  const fetchData = () => {
    itemRefs.value?.forEach((item) => {
      item.fetchData();
    });
  };

  const handleClearSearch = () => {
    emits('clear-search');
  };

  defineExpose<Exposed>({
    fetchData,
  });
</script>
