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
    onBeforeUnmount,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useUrlSearch } from '@hooks';

  import { useMainViewStore } from '@stores';

  import BackupInspection from './components/backup-inspection/Index.vue';
  import DataValidation from './components/data-validation/Index.vue';
  import MetadataCheck from './components/metadata-check/Index.vue';
  import SearchBox from './components/SearchBox.vue';

  const URL_MEMO_KEY = 'tabType';

  const route = useRoute();
  const { t } = useI18n();
  const mainViewStore = useMainViewStore();
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
    } as Record<string, any>;

    return comMap[tabType.value];
  });

  watch(() => route.fullPath, () => {
    mainViewStore.hasPadding = false;
  }, {
    immediate: true,
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

  onBeforeUnmount(() => {
    mainViewStore.hasPadding = true;
  });
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
