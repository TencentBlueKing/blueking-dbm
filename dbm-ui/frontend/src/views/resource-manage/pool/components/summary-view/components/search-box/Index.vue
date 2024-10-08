<template>
  <BkForm
    class="search-box"
    form-type="vertical">
    <BkFormItem
      :label="t('所属业务')"
      required>
      <Biz
        :model="searchParams"
        @change="handleSearch" />
    </BkFormItem>
    <BkFormItem
      :label="t('所属DB类型')"
      required>
      <Db
        :model="searchParams"
        @change="(data) => handleSearch(data, 'db')" />
    </BkFormItem>
    <BkFormItem :label="t('地域 - 园区')">
      <Region
        :model="searchParams"
        @change="handleSearch" />
    </BkFormItem>
    <BkFormItem :label="t('规格')">
      <Spec
        :model="searchParams"
        @change="handleSearch" />
    </BkFormItem>
  </BkForm>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useUrlSearch } from '@hooks';

  import Biz from './components/Biz.vue';
  import Db from './components/Db.vue';
  import Region from './components/Region.vue';
  import Spec from './components/Spec.vue';

  interface Emits {
    (e: 'search'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();

  const searchParams = ref(getSearchParams());

  const filterEmptyValues = (obj: any): any =>
    _.pickBy(obj, (value) => value !== '' && (!_.isArray(value) || !_.isEmpty(value)));

  const handleSearch = (data = {} as Record<string, string | number>, type?: string, isInit = false) => {
    let params = getSearchParams();
    Object.assign(params, data);
    if (params.db_type !== 'PUBLIC' && params.db_type !== params.cluster_type) {
      params.cluster_type = params.db_type;
      delete params.machine_type;
      delete params.spec_id_list;
    }
    if ((type === 'db' && data.db_type === 'PUBLIC') || (isInit && params.db_type === 'PUBLIC')) {
      delete params.cluster_type;
      delete params.machine_type;
      delete params.spec_id_list;
    }
    if (isInit) {
      // 初始化一定要带db_type和业务id
      params.db_type = params.db_type || 'PUBLIC';
      params.for_biz = params.for_biz || '0';
    }
    params = filterEmptyValues(params);
    replaceSearchParams(params);
    searchParams.value = params;
    emits('search');
  };

  onMounted(() => {
    handleSearch({}, '', true);
  });

  onActivated(() => {
    handleSearch({}, '', true);
  });
</script>

<style lang="less" scoped>
  .search-box {
    display: flex;

    :deep(.bk-form-item) {
      margin-bottom: 0;

      .bk-form-label {
        font-weight: initial;
      }

      & ~ .bk-form-item {
        margin-left: 16px;
      }

      &:nth-child(-n + 2) {
        flex: 1;
      }

      &:nth-last-child(2) {
        flex: 1.5;
      }

      &:nth-last-child(1) {
        flex: 2;
      }
    }
  }
</style>
