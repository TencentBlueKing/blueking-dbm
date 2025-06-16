<template>
  <BkLoading
    class="bussiness-dashboard"
    :loading="businessDashboardLoading">
    <template v-if="businessDashboardData?.urls.length">
      <DbTab
        v-model="activePanelKey"
        :exclude="excludeDbTyps" />
      <div class="bussiness-dashboard-content">
        <MonitorDashboard :url="currentItem?.url" />
      </div>
    </template>
    <BkException
      v-else
      class="empty-exception"
      :description="t('暂无数据')"
      scene="part"
      type="empty" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBusinessDashboard } from '@services/source/monitorGrafana';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import MonitorDashboard from '@views/db-manage/common/cluster-monitor/MonitorDashboard.vue';

  const { t } = useI18n();

  const {
    data: businessDashboardData,
    loading: businessDashboardLoading,
    run: runBusinessDashboard,
  } = useRequest(getBusinessDashboard, {
    manual: true,
  });

  const activePanelKey = ref('' as DBTypes);

  const excludeDbTyps = computed(() => {
    const urlDbTypeMap = Object.fromEntries(
      (businessDashboardData.value?.urls || []).map((urlItem) => [urlItem.db_type, true]),
    );
    return Object.values(DBTypeInfos).reduce<DBTypes[]>((prevList, dbItem) => {
      if (!urlDbTypeMap[dbItem.id]) {
        return prevList.concat(dbItem.id);
      }
      return prevList;
    }, []);
  });

  const currentItem = computed(() =>
    businessDashboardData.value?.urls.find((urlItem) => urlItem.db_type === activePanelKey.value),
  );

  const fetchData = () => {
    runBusinessDashboard({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };
  fetchData();
</script>

<style lang="less">
  .bussiness-dashboard {
    height: 100%;

    .bussiness-dashboard-content {
      height: calc(100% - 43px);
      padding: 24px;
    }

    .empty-exception {
      display: flex;
      height: 100%;
      background-color: #fff;
      align-items: center;
      justify-content: center;
    }
  }
</style>
