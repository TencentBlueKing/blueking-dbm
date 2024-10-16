<template>
  <BkForm
    class="search-box"
    form-type="vertical">
    <BkFormItem
      :label="t('所属业务')"
      required>
      <Biz
        ref="bizRef"
        :model="searchParams"
        @change="handleSearch" />
    </BkFormItem>
    <BkFormItem
      :label="t('所属DB类型')"
      required>
      <Db
        ref="dbRef"
        :model="searchParams"
        @change="handleSearch" />
    </BkFormItem>
    <BkFormItem :label="t('地域 - 园区')">
      <Region
        ref="regionRef"
        :model="searchParams"
        @change="handleSearch" />
    </BkFormItem>
    <BkFormItem :label="t('规格')">
      <Spec
        ref="specRef"
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

  const bizRef = ref<InstanceType<typeof Biz>>();
  const dbRef = ref<InstanceType<typeof Db>>();
  const regionRef = ref<InstanceType<typeof Region>>();
  const specRef = ref<InstanceType<typeof Spec>>();
  const searchParams = ref(getSearchParams());

  const filterEmptyValues = (obj: any): any =>
    _.pickBy(obj, (value) => value !== '' && (!_.isArray(value) || !_.isEmpty(value)));

  const handleSearch = () => {
    Promise.all([
      bizRef.value!.getValue(),
      dbRef.value!.getValue(),
      regionRef.value!.getValue(),
      specRef.value!.getValue(),
    ]).then(([biz, db, region, spec]) => {
      const parmas = filterEmptyValues({
        ...biz,
        ...db,
        ...region,
        ...spec,
      });
      replaceSearchParams(parmas);
      searchParams.value = parmas;
      emits('search');
    });
  };

  onMounted(() => {
    handleSearch();
  });

  onActivated(() => {
    handleSearch();
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
