<template>
  <DbSearchSelect
    class="mb-16"
    :data="searchSelectData"
    :model-value="searchSelectValue"
    :placeholder="t('请输入或选择条件搜索')"
    unique-select
    @change="handleSearchChange" />
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  export type SearchSelectList = {
    id: string,
    name: string,
    children?: {
      id: string | number,
      name: string,
    }[]
  }[]

  interface Props {
    searchAttrs: SearchAttrs
  }

  interface Emits {
    (e: 'searchValueChange', value: ISearchValue[]): void,
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();

  const searchSelectData = computed(() => [
    {
      name: t('实例'),
      id: 'instance',
      multiple: true,
    },
    {
      name: t('实例状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'running',
          name: t('正常'),
        },
        {
          id: 'unavailable',
          name: t('异常'),
        },
        {
          id: 'loading',
          name: t('重建中'),
        },
      ],
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: props.searchAttrs.bk_cloud_id,
    },
  ]);

  const handleSearchChange = (value: ISearchValue[]) => {
    emits('searchValueChange', value);
  };
</script>
