<template>
  <DbSearchSelect
    v-model="searchSelectValue"
    class="mb-16"
    :data="searchSelectData"
    :placeholder="$t('域名_模块')"
    unique-select
    @change="handleSearch" />
</template>
<script setup lang="ts">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/common';

  import { useGlobalBizs } from '@stores';

  interface Props {
    clusterType: string,
  }

  interface Emits {
    (e: 'search'): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const searchSelectValue = defineModel<ISearchValue[]>({
    default: [],
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const dbModuleList = shallowRef<{ id: number, name: string }[]>([]);

  const searchSelectData = computed(() => [{
    name: t('主访问入口'),
    id: 'domain',
  }, {
    name: t('模块'),
    id: 'db_module_id',
    children: dbModuleList.value,
  }]);

  const { run: rungGetModules } = useRequest(getModules, {
    manual: true,
    onSuccess(res) {
      dbModuleList.value = res.map(item => ({
        id: item.db_module_id,
        name: item.name,
      }));
    },
  });

  watch(() => props.clusterType, (type) => {
    if (type) {
      rungGetModules({
        bk_biz_id: currentBizId,
        cluster_type: type,
      });
    }
  }, {
    immediate: true,
  });

  const handleSearch = () => {
    emits('search');
  };
</script>
