<template>
  <div class="global-staff-manage-biz-manage">
    <BkTab
      v-model:active="activeBizSubTab"
      class="biz-manage-tab"
      type="card-tab">
      <BkTabPanel
        v-for="tab of bizSubTabs"
        :key="tab.key"
        :label="tab.label"
        :name="tab.key">
        <Managed
          v-if="activeBizSubTab === 'managed'"
          :key="activeBizSubTab" />
        <UnManaged
          v-if="activeBizSubTab === 'unmanaged'"
          :key="activeBizSubTab" />
      </BkTabPanel>
    </BkTab>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import Managed from './components/managed/Index.vue';
  import UnManaged from './components/unmanaged/Index.vue';

  const { t } = useI18n();

  const bizSubTabs = [
    { key: 'managed', label: t('已纳管') },
    { key: 'unmanaged', label: t('未纳管') },
  ];

  const activeBizSubTab = ref<'managed' | 'unmanaged'>('managed');
</script>

<style lang="less">
  .global-staff-manage-biz-manage {
    padding: 20px 24px;

    .biz-manage-tab {
      background-color: #fff;
      box-shadow: 0 2px 6px 0 #0000001a;
    }
  }
</style>
