<!--
  * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
  *
  * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
  *
  * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
  * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
  *
  * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
  * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
  * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="biz-staff-manage-dba">
    <BkLoading :loading="isLoading">
      <BkTab
        v-model:active="activeTopTab"
        class="db-manage-tab"
        type="card-tab">
        <BkTabPanel
          v-for="tab of topTabs"
          :key="tab.key"
          :label="tab.label"
          :name="tab.key"
          :num="tab.count"
          num-display-type="bracket" />
      </BkTab>
      <div class="db-manage-content">
        <Table
          v-if="activeTopTab"
          :data="tableData"
          :default-admins-data-map="defaultAdminsDataMap"
          :user-data-map="userDataMap"
          @suceess="handleSucess" />
      </div>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins } from '@services/source/dbadmin';
  import { queryClusterInstanceCount } from '@services/source/dbbase';
  import { getUserList } from '@services/source/user';

  import { ClusterCountMap, ClusterTypes, DBTypeInfos, DBTypes } from '@common/const';

  import Table from './components/Table.vue';

  interface Props {
    countData?: ServiceReturnType<typeof queryClusterInstanceCount>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const activeTopTab = ref<'apply' | 'unapply'>('apply');

  const getDefaultDbTypeAdmin = (dbType: DBTypes) => ({
    bk_biz_id: 0,
    db_type: dbType,
    db_type_display: DBTypeInfos[dbType as DBTypes].name,
    is_show: true,
    update_at: '',
    updater: '',
    users: [] as string[],
  });

  const dbTypeMap = computed(() => {
    const applyDbTypes: DBTypes[] = [];
    const unapplyDbTypes: DBTypes[] = [];

    if (props.countData) {
      Object.keys(DBTypeInfos).forEach((dbType) => {
        const clusterTypes = ClusterCountMap[dbType];
        let clusterCount = 0;

        if (clusterTypes) {
          clusterCount = clusterTypes.reduce(
            (prevCount, key) => prevCount + (props.countData![key as ClusterTypes].cluster_count || 0),
            0,
          );
        } else {
          clusterCount = props.countData![dbType as ClusterTypes].cluster_count || 0;
        }

        if (clusterCount > 0) {
          applyDbTypes.push(dbType as DBTypes);
        } else {
          unapplyDbTypes.push(dbType as DBTypes);
        }
      });
    }

    return {
      applyDbTypes,
      unapplyDbTypes,
    };
  });

  const topTabs = computed(() => [
    { count: dbTypeMap.value.applyDbTypes.length, key: 'apply', label: t('已部署的组件') },
    { count: dbTypeMap.value.unapplyDbTypes.length, key: 'unapply', label: t('未部署的组件') },
  ]);

  const tableData = computed(() => {
    const activeDbTypes =
      activeTopTab.value === 'apply' ? dbTypeMap.value.applyDbTypes : dbTypeMap.value.unapplyDbTypes;
    const bizAdminsMap = Object.fromEntries(
      Object.values(bizAdminsData.value || {}).map((item) => [item.db_type, item]),
    );

    return activeDbTypes.map((item) => bizAdminsMap[item] || getDefaultDbTypeAdmin(item));
  });

  const defaultAdminsDataMap = computed(() => {
    const defalutAdminsMap = Object.fromEntries(
      Object.values(defalutAdminsData.value || {}).map((item) => [item.db_type, item]),
    );
    const defalutAdminsList = Object.values(DBTypeInfos).map(
      (item) => defalutAdminsMap[item.id] || getDefaultDbTypeAdmin(item.id),
    );
    return Object.fromEntries(defalutAdminsList.map((item) => [item.db_type, item]));
  });
  const userDataMap = computed(() =>
    Object.fromEntries((userData.value?.results || []).map((item) => [item.username, item.display_name])),
  );
  const isLoading = computed(
    () => isGetDefalutAdminsLoading.value || isGetBizAdminsLoading.value || isGetUserListLoading.value,
  );

  const {
    data: defalutAdminsData,
    loading: isGetDefalutAdminsLoading,
    run: runGetDefalutAdmins,
  } = useRequest(getAdmins, {
    manual: true,
  });

  const {
    data: bizAdminsData,
    loading: isGetBizAdminsLoading,
    run: runGetBizAdmins,
  } = useRequest(getAdmins, {
    manual: true,
  });

  const { data: userData, loading: isGetUserListLoading } = useRequest(getUserList);

  const fetchData = () => {
    runGetDefalutAdmins({
      bk_biz_id: 0,
    });
    runGetBizAdmins({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
  };
  fetchData();

  const handleSucess = () => {
    fetchData();
  };
</script>

<style lang="less">
  .biz-staff-manage-dba {
    padding: 20px 24px;

    .db-manage-tab {
      .bk-tab-content {
        padding: 0;
      }
    }

    .db-manage-content {
      background-color: #fff;
      box-shadow: 0 2px 6px 0 #0000001a;
    }
  }
</style>
