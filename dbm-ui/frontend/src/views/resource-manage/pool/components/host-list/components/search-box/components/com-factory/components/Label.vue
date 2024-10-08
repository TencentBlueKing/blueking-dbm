<template>
  <BkSelect
    class="tag-research-selector"
    filterable
    :model-value="selected"
    multiple
    multiple-mode="tag"
    :remote-method="handleSearch"
    :scroll-loading="isLoading"
    selected-style="checkbox"
    @change="handleChange"
    @scroll-end="loadMore">
    <BkOption
      v-for="item in tagList"
      :key="item.id"
      :label="item.value"
      :value="item.id" />
  </BkSelect>
</template>

<script setup lang="tsx">
  import { uniqBy } from 'lodash';
  import { useRequest } from 'vue-request';

  import type DbResource from '@services/model/db-resource/DbResource';
  import { listTag } from '@services/source/tag';

  interface Props {
    defaultValue: string;
  }

  interface Emits {
    (e: 'change', value: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    defaultValue: '',
  });

  const emits = defineEmits<Emits>();

  const searchVal = ref('');
  const tagList = ref<ServiceReturnType<typeof listTag>['results']>([]);
  const selected = ref<DbResource['labels'][number]['id'][]>([]);
  const pagination = reactive({
    offset: 0,
    limit: 10,
    count: 0,
  });

  const { run: runList, loading: isLoading } = useRequest(listTag, {
    manual: true,
    onSuccess(data) {
      pagination.count = data.count;
      tagList.value = uniqBy([...tagList.value, ...data.results], 'value');
    },
  });

  const { runAsync: runAsyncList } = useRequest(listTag);

  watch(
    () => props.defaultValue,
    async () => {
      if (props.defaultValue) {
        selected.value = props.defaultValue.split(',').map((v) => +v);
        const { results } = await runAsyncList({
          ids: props.defaultValue,
        });
        tagList.value = uniqBy([...tagList.value, ...results], 'value');
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  watch(searchVal, () => {
    pagination.offset = 0;
    pagination.count = 0;
    tagList.value = [];
    runList({
      ...pagination,
      value: searchVal.value,
    });
  });

  const loadMore = () => {
    if (pagination.offset >= pagination.count || isLoading.value) {
      return;
    }
    pagination.offset = Math.min(pagination.count, pagination.offset + pagination.limit);
    runList({
      ...pagination,
      value: searchVal.value,
    });
  };

  const handleChange = (value: string[]) => {
    emits('change', value.join(','));
  };

  const handleSearch = (val: string) => {
    searchVal.value = val;
  };

  onMounted(() => {
    runList(pagination);
  });
</script>
