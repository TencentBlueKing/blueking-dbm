<template>
  <DbSearchSelect
    class="mb-16"
    :data="searchSelectData"
    :model-value="searchSelectValue"
    :placeholder="t('请输入或选择条件搜索')"
    unique-select
    :validate-values="validateSearchValues"
    @change="handleSearchChange" />
</template>
<script setup lang="ts">
  import type { ISearchValue, ValidateValuesFunc } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import type { SearchAttrs } from '@hooks';

  export type SearchSelectList = {
    children?: {
      id: string | number;
      name: string;
    }[];
    id: string;
    name: string;
  }[];

  interface Props {
    isHost?: boolean;
    searchAttrs: SearchAttrs;
    type?: string;
    validateSearchValues: ValidateValuesFunc;
  }

  type Emits = (e: 'searchValueChange', value: ISearchValue[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    isHost: false,
    type: '',
  });

  const emits = defineEmits<Emits>();

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();

  const isHideStatus = computed(() => (props.type && props.type === 'redis') || props.isHost);

  const searchSelectData = computed(() => {
    const basicSelct = [
      {
        id: props.isHost ? 'ip' : 'instance',
        multiple: true,
        name: props.isHost ? 'IP' : t('IP 或 IP:Port'),
      },
      {
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
        id: 'status',
        multiple: true,
        name: t('实例状态'),
      },
      {
        children: props.searchAttrs.bk_cloud_id,
        id: 'bk_cloud_id',
        multiple: true,
        name: t('管控区域'),
      },
    ];
    if (isHideStatus.value) {
      basicSelct.splice(1, 1);
    }
    return basicSelct;
  });

  const handleSearchChange = (value: ISearchValue[]) => {
    emits('searchValueChange', value);
  };
</script>
