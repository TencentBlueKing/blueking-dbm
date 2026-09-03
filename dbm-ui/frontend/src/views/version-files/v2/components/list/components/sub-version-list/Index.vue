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
  <div class="sub-version-list-main">
    <div
      v-if="isReleaseEmpty"
      class="release-empty-main">
      <BkException
        :description="t('请先在左侧添加发行版')"
        type="empty" />
    </div>
    <template v-else>
      <div
        v-if="versionSeriesList && versionSeriesList.length"
        class="title-operate-main">
        <div class="title-operate-left">
          <AuthButton
            action-id="package_manage"
            :permission="commonPermission"
            :resource="dbType"
            theme="primary"
            @click="handleAddVersion">
            <DbIcon type="add" />
            <span class="ml-6">{{ t('添加版本') }}</span>
          </AuthButton>
          <div
            v-if="isPureMysql"
            class="main-title ml-12">
            {{ releaseVersion?.name }}
          </div>
          <I18nT
            class="ml-12"
            keypath="共n个版本"
            tag="span">
            <template #n>
              <BkTag radius="12px">{{ dbVersionListCount }}</BkTag>
            </template>
          </I18nT>
        </div>
        <DbQuickSearch
          v-model="searchValue"
          :data="searchSelectData"
          :placeholder="t('搜索版本名，版本阶段，版本号，启停，描述，更新人')"
          style="width: 670px"
          unique-select
          value-split-code=","
          @change="handleSearchChange" />
      </div>
      <div
        v-if="versionSeriesList && versionSeriesList.length > 0"
        ref="versionsListRef"
        class="versions-list-main">
        <TableList
          ref="subVersionRefs"
          :db-type="dbType"
          :db-version-list="dbVersionList"
          :loading="isDbVersionListLoading"
          :permission="commonPermission"
          :version-series-list="versionSeriesList"
          @add-new-version="handleAddNewDbVersion"
          @edit-db-version="(data) => handleEditDbVersion(data)"
          @filter-value-change="handleFilterValueChange"
          @refresh-db-version-list="fetchDbVersionList"
          @refresh-release-list="() => emits('refreshReleaseList')"
          @refresh-version-list="fetchVersionSeriesList" />
      </div>
      <div v-else>
        <BkException
          class="release-empty-main"
          type="empty">
          <span>{{ t('暂无版本') }}</span>
          <span class="ml-4 mr-4">,</span>
          <AuthButton
            action-id="package_manage"
            :permission="commonPermission"
            :resource="dbType"
            size="small"
            text
            theme="primary"
            @click="handleAddVersion">
            {{ t('立即添加') }}
          </AuthButton>
        </BkException>
      </div>
    </template>
  </div>
  <EditVersion
    v-model:is-show="isShowEditVersion"
    :db-type="dbType"
    :db-version="currentDbVersion"
    :is-edit="isEditVersion"
    :pkg-type="pkgType"
    :release-version="releaseVersion"
    :version-num="versionNum"
    :version-series-id="currentVersionSeriesId"
    @add-version="handleAddVersionSuccess"
    @success="handleEditVersionSuccess" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { getDbVersionList, getVersionSeriesList } from '@services/source/version';

  import { isPureMysqlPkgType } from '@views/version-files/v2/common';

  import EditVersion from './components/edit-version/Index.vue';
  import TableList from './components/table-list/Index.vue';
  import useVersionFilter from './hooks/useVersionFilter';

  interface Props {
    dbType: string;
    hasPackageManagePermission: boolean;
    pkgType: string;
    releaseVersion?: ReleaseVersionModel;
    versionNum: number;
  }

  type Emits = (e: 'refreshReleaseList') => void;

  interface Exposes {
    clearFilter: () => void;
    showReleaseEmpty: (isShow: boolean) => void;
  }

  type VersionSeriesModel = ServiceReturnType<typeof getVersionSeriesList>[number];

  const props = withDefaults(defineProps<Props>(), {
    releaseVersion: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});
  const subVersionRefs = ref<InstanceType<typeof TableList>>();
  const isShowEditVersion = ref(false);
  const isEditVersion = ref(false);
  const isReleaseEmpty = ref(false);
  const currentVersionSeriesId = ref(0);
  const currentDbVersion = ref<DbVersionModel>();

  const isPureMysql = computed(() => isPureMysqlPkgType(props.dbType, props.pkgType));
  const commonPermission = computed(
    () => props.releaseVersion?.permission.package_manage || props.hasPackageManagePermission,
  );
  const { data: versionSeriesList, run: runGetVersionSeriesList } = useRequest(getVersionSeriesList, {
    manual: true,
  });

  // 版本列表放在这里请求，搜索栏的版本号候选项与表格共用同一份数据
  const {
    data: dbVersionList,
    loading: isDbVersionListLoading,
    run: runGetDbVersionList,
  } = useRequest(getDbVersionList, {
    manual: true,
  });

  const dbVersionListCount = computed(() => dbVersionList.value?.length || 0);

  const { searchSelectData } = useVersionFilter(dbVersionList);

  const fetchVersionSeriesList = () => {
    if (!props.releaseVersion) {
      return;
    }
    runGetVersionSeriesList({
      distribution: props.releaseVersion.id,
    });
  };

  const fetchDbVersionList = () => {
    if (!versionSeriesList.value?.length) {
      return;
    }
    runGetDbVersionList({
      version_series__in: versionSeriesList.value.map((item) => item.id).join(','),
    });
  };

  watch(() => props.releaseVersion, fetchVersionSeriesList, {
    immediate: true,
  });

  watch(versionSeriesList, fetchDbVersionList);

  const handleAddVersionSuccess = () => {
    fetchVersionSeriesList();
    emits('refreshReleaseList');
  };

  // 搜索栏与表头筛选的值形态一致（逗号分隔字符串），两边直接互传
  const handleSearchChange = (value: Record<string, string>) => {
    subVersionRefs.value?.setFilterValue(value);
  };

  const handleFilterValueChange = (value: Record<string, string>) => {
    searchValue.value = value;
  };

  const handleEditDbVersion = (data: DbVersionModel) => {
    currentDbVersion.value = data;
    currentVersionSeriesId.value = data.version_series;
    isShowEditVersion.value = true;
    isEditVersion.value = true;
  };

  const handleAddNewDbVersion = (versionSeries: VersionSeriesModel) => {
    currentVersionSeriesId.value = versionSeries.id;
    isShowEditVersion.value = true;
    isEditVersion.value = false;
    currentDbVersion.value = undefined;
    emits('refreshReleaseList');
  };

  const handleAddVersion = () => {
    currentVersionSeriesId.value = 0;
    isShowEditVersion.value = true;
    isEditVersion.value = false;
    currentDbVersion.value = undefined;
  };

  const handleEditVersionSuccess = (versionSeriesId: number) => {
    emits('refreshReleaseList');
    // 版本仍在已加载的系列里就只刷新版本列表，落到新系列时要重新拉系列列表
    if (versionSeriesList.value?.some((item) => item.id === versionSeriesId)) {
      fetchDbVersionList();
      return;
    }
    fetchVersionSeriesList();
  };

  defineExpose<Exposes>({
    clearFilter: () => {
      subVersionRefs.value?.clearFilter();
    },
    showReleaseEmpty: (isShow: boolean) => {
      isReleaseEmpty.value = isShow;
    },
  });
</script>
<style lang="less">
  .sub-version-list-main {
    display: flex;
    padding: 0 16px;
    flex: 1;
    flex-direction: column;
    overflow: hidden;

    .release-empty-main {
      margin-top: 60px;

      .bk-exception-description {
        margin-top: 0;
      }

      .bk-exception-footer {
        margin-top: 0;
      }
    }

    .versions-list-main {
      display: flex;
      overflow-y: auto;
      flex: 1;
      flex-direction: column;
    }

    .title-operate-main {
      display: flex;
      height: 32px;
      align-items: center;
      margin-bottom: 20px;

      .title-operate-left {
        flex: 1;
        display: flex;
        margin-right: 8px;
        align-items: center;

        .main-title {
          font-size: 16px;
          font-weight: 700;
          color: #313238;
        }
      }
    }
  }
</style>
