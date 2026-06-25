<template>
  <div class="global-staff-manage-db-manage">
    <DbTab
      v-model:active="activeTab"
      class="db-manage-tab"
      :suffix-items="[
        {
          id: 'default-dba',
          name: t('默认 DBA'),
        },
      ]"
      type="card-tab" />
    <div class="db-manage-content">
      <DbTypePanel
        v-if="activeTab && activeTab !== 'default-dba'"
        :key="activeTab"
        :active-tab="activeTab" />
      <DefaultDbaPanel v-if="activeTab && activeTab === 'default-dba'" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbTab from '@components/db-tab/Index.vue';

  import DbTypePanel from './components/db-type/Index.vue';
  import DefaultDbaPanel from './components/default-dba/Index.vue';

  const { t } = useI18n();

  const activeTab = ref('');
</script>

<style lang="less">
  .global-staff-manage-db-manage {
    padding: 20px 24px;

    .db-manage-tab {
      padding: 0;
      box-shadow: none;
    }

    .db-manage-content {
      background-color: #fff;
      box-shadow: 0 2px 6px 0 #0000001a;
    }
  }
</style>
