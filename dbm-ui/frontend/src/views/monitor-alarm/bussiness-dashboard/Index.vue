<template>
  <BkLoading
    class="bussiness-dashboard"
    :loading="isLoading">
    <BkTab
      v-model:active="activePanelKey"
      class="bussiness-dashboard-tab"
      type="unborder-card">
      <BkTabPanel
        v-for="item in tabList"
        :key="item.value"
        :label="item.label"
        :name="item.value" />
    </BkTab>
    <div class="bussiness-dashboard-content">
      <MonitorDashboard
        v-if="currentItem?.url"
        :url="currentItem.url" />
      <BkException
        v-else
        class="content-exception"
        :description="t('暂无数据')"
        scene="part"
        type="empty" />
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { BigdataFunctions } from '@services/model/function-controller/functionController';
  import { getBizSettingList } from '@services/source/bizSetting';
  import { getBusinessDashboard } from '@services/source/monitorGrafana';

  import { useFunController } from '@stores';

  import { BizSettingKeys, DBTypeInfos, DBTypes } from '@common/const';

  import MonitorDashboard from '@views/db-manage/common/cluster-monitor/MonitorDashboard.vue';

  const { t } = useI18n();
  const funControllerStore = useFunController();

  const { data: bizSettingData, loading: bizSettingLoading } = useRequest(getBizSettingList, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        key: BizSettingKeys.DATABASE_MANAGE_MENU,
      },
    ],
  });

  const {
    data: businessDashboardData,
    loading: businessDashboardLoading,
    run: runBusinessDashboard,
  } = useRequest(getBusinessDashboard, {
    manual: true,
  });

  const activePanelKey = ref('');

  const isLoading = computed(() => bizSettingLoading.value || businessDashboardLoading.value);

  const tabList = computed(() => {
    if (
      bizSettingData.value &&
      bizSettingData.value[BizSettingKeys.DATABASE_MANAGE_MENU] &&
      bizSettingData.value[BizSettingKeys.DATABASE_MANAGE_MENU].length > 0 &&
      businessDashboardData.value &&
      businessDashboardData.value.urls.length > 0
    ) {
      const urlDbTypeMap = Object.fromEntries(
        businessDashboardData.value.urls.map((urlItem) => [urlItem.db_type, true]),
      );
      return (bizSettingData.value[BizSettingKeys.DATABASE_MANAGE_MENU] as DBTypes[]).reduce<
        {
          label: string;
          value: string;
        }[]
      >((prevList, dbType) => {
        const dbTypeInfo = DBTypeInfos[dbType];
        if (dbTypeInfo && urlDbTypeMap[dbType]) {
          if (dbTypeInfo.moduleId === 'bigdata') {
            const data = funControllerStore.funControllerData.getFlatData(dbTypeInfo.moduleId);
            if (data[dbType as BigdataFunctions])
              return prevList.concat({
                label: dbTypeInfo.name,
                value: dbType,
              });
          } else {
            const controllerData = funControllerStore.funControllerData[dbTypeInfo.moduleId];
            if (controllerData.is_enabled) {
              return prevList.concat({
                label: dbTypeInfo.name,
                value: dbType,
              });
            }
          }
        }
        return prevList;
      }, []);
    }

    return [];
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

    .bussiness-dashboard-tab {
      padding: 0 24px;
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content {
        display: none;
      }
    }

    .bussiness-dashboard-content {
      height: calc(100% - 43px);
      padding: 24px;

      .content-exception {
        display: flex;
        height: 100%;
        background-color: #fff;
        align-items: center;
        justify-content: center;
      }
    }
  }
</style>
