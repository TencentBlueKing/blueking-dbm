<template>
  <div class="global-staff-manage-db-manage">
    <DbTab
      v-model:active="activeTab"
      class="db-manage-tab"
      :suffix-items="[
        {
          id: DEFAULT_DBA_TAB,
          name: t('默认 DBA'),
        },
      ]"
      type="card-tab" />
    <div class="db-manage-content">
      <DbTypePanel
        v-if="activeTab && activeTab !== DEFAULT_DBA_TAB"
        :key="activeTab"
        :active-tab="activeTab" />
      <DefaultDbaPanel v-if="activeTab && activeTab === DEFAULT_DBA_TAB" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypeInfos } from '@common/const/index.ts';

  import DbTab from '@components/db-tab/Index.vue';

  import DbTypePanel from './components/db-type/Index.vue';
  import DefaultDbaPanel from './components/default-dba/Index.vue';

  interface Props {
    activeTopTab: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const DEFAULT_DBA_TAB = 'default-dba';

  const activeTab = ref('');

  watch(
    activeTab,
    () => {
      nextTick(() => {
        router.replace({
          params: {
            subTabType: activeTab.value,
            tabType: props.activeTopTab,
          },
        });
      });
    },
    {
      immediate: true,
    },
  );

  onMounted(() => {
    const subTabType = route.params.subTabType as string;
    const tabKeys = Object.keys(DBTypeInfos).concat(DEFAULT_DBA_TAB);
    if (subTabType && tabKeys.includes(subTabType)) {
      activeTab.value = subTabType;
    }
  });

  onBeforeUnmount(() => {
    router.replace({
      params: {
        subTabType: '',
        tabType: props.activeTopTab,
      },
    });
  });
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
