<template>
  <BkSearchSelect
    v-model="modelValue"
    class="search-selector"
    :data="searchSelectData"
    unique-select
    value-split-code="+"
    @search="handleSearch" />
</template>

<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  interface Emits {
    (e: 'search'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const modelValue = defineModel<ISearchValue[]>({
    default: () => [],
  });
  const deviceClassList = ref<ServiceReturnType<typeof fetchDeviceClass>['results']>([]);

  const searchSelectData = computed(() => [
    {
      name: 'IP',
      id: 'ips',
    },
    {
      name: t('地域'),
      id: 'city',
    },
    {
      name: t('园区'),
      id: 'sub_zone',
    },
    {
      name: t('机架'),
      id: 'rack_id',
    },
    {
      name: t('操作系统'),
      id: 'os_name',
    },
    {
      name: t('机型'),
      id: 'device_class',
      children: deviceClassList.value?.map((item) => ({
        id: item,
        name: item,
      })),
    },
  ]);

  useRequest(fetchDeviceClass, {
    onSuccess: (deviceClassRes) => {
      deviceClassList.value = deviceClassRes.results;
    },
  });

  const handleSearch = () => {
    emits('search');
  };
</script>

<style scoped lang="less">
  .fault-or-recycle-search-selector {
    width: 560px;
    height: 32px;
    margin-left: auto;
  }
</style>
