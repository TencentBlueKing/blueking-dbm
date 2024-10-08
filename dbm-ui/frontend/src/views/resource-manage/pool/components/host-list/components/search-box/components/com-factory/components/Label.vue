<template>
  <BkSelect
    class="tag-research-selector"
    filterable
    :model-value="selected"
    multiple
    multiple-mode="tag"
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
      tagList.value.push(...data.results);
    },
  });

  watch(
    () => props.defaultValue,
    () => {
      if (props.defaultValue) {
        selected.value = props.defaultValue.split(',').map((v) => +v);
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  const loadMore = () => {
    if (tagList.value.length >= pagination.count || isLoading.value) {
      return;
    }
    pagination.offset += pagination.limit;
    runList(pagination);
  };

  const handleChange = (value: string[]) => {
    emits('change', value.join(','));
  };

  onMounted(() => {
    runList(pagination);
  });
</script>
