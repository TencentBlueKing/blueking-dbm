<template>
  <div class="inspection-manage-page">
    <BkTab
      v-model:active="tabType"
      class="list-type-box"
      type="unborder-card">
      <BkTabPanel
        :label="t('备份巡检')"
        name="backupInspection" />
      <BkTabPanel
        :label="t('数据校验')"
        name="dataValidation" />
      <BkTabPanel
        :label="t('元数据检查')"
        name="metadataCheck" />
      <BkTabPanel
        :label="t('其它')"
        name="more" />
    </BkTab>
    <div class="content-wrapper">
      <SearchBox
        style="margin-bottom: 30px;"
        @change="handleSearchChange" />
      <Component
        :is="renderCom"
        :search-params="serachParams" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    computed,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useUrlSearch } from '@hooks';

  import BackupInspection from './components/backup-inspection/Index.vue';
  import DataValidation from './components/data-validation/Index.vue';
  import MetadataCheck from './components/metadata-check/Index.vue';
  import More from './components/more/Index.vue';
  import SearchBox from './components/SearchBox.vue';

  const URL_MEMO_KEY = 'tabType';

  const { t } = useI18n();
  const {
    appendSearchParams,
    getSearchParams,
    replaceSearchParams,
  } = useUrlSearch();

  const tabType = ref(getSearchParams()[URL_MEMO_KEY] || 'backupInspection');
  const serachParams = ref<Record<string, any>>({});

  const renderCom = computed(() => {
    const comMap = {
      backupInspection: BackupInspection,
      dataValidation: DataValidation,
      metadataCheck: MetadataCheck,
      more: More,
    } as Record<string, any>;

    return comMap[tabType.value];
  });

  watch(tabType, () => {
    appendSearchParams({
      [URL_MEMO_KEY]: tabType.value,
    });
  });

  const handleSearchChange = (payload: Record<string, any>) => {
    serachParams.value = payload;
    replaceSearchParams({
      [URL_MEMO_KEY]: tabType.value,
      ...payload,
    });
  };

</script>
<style lang="less">
  .inspection-manage-page {
    .list-type-box{
      background-color: #fff;

      .bk-tab-content{
        display: none;
      }

      .bk-tab-header{
        border: none;
        box-shadow: 0 3px 4px 0 #0000000a;
      }
    }

    .content-wrapper{
      padding: 20px;
    }
  }
</style>
