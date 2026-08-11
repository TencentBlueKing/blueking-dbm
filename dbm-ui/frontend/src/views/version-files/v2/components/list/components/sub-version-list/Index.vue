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
          :key="renderSearchKey"
          v-model="searchValue"
          :data="searchSelectData"
          :placeholder="t('搜索版本名，版本阶段，版本号，是否启用，描述，更新人')"
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
          :permission="commonPermission"
          :version-series-list="versionSeriesList"
          @add-new-version="handleAddNewDbVersion"
          @edit-db-version="(data) => handleEditDbVersion(data)"
          @filter-value-change="handleFilterValueChange"
          @list-change="handleTableListChange"
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { getVersionSeriesList } from '@services/source/version';

  // import ScrollFaker from '@components/scroll-faker/Index.vue';
  import EditVersion from './components/edit-version/Index.vue';
  import TableList from './components/table-list/Index.vue';
  // import SubVersion from './components/sub-version/Index.vue';
  import useSearch from './hooks/useSearch';

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
  const { searchSelectData, searchValue } = useSearch();

  const subVersionRefs = ref<InstanceType<typeof TableList>>();
  const renderSearchKey = ref(0);
  const isShowEditVersion = ref(false);
  const isEditVersion = ref(false);
  const isReleaseEmpty = ref(false);
  const currentVersionSeriesId = ref(0);
  const dbVersionListCount = ref(0);
  const currentDbVersion = ref<DbVersionModel>();

  const isPureMysql = computed(() => props.dbType === 'mysql' && props.pkgType === 'mysql');
  const commonPermission = computed(
    () => props.releaseVersion?.permission.package_manage || props.hasPackageManagePermission,
  );

  const { data: versionSeriesList, run: runGetVersionSeriesList } = useRequest(getVersionSeriesList, {
    manual: true,
  });

  const fetchVersionSeriesList = () => {
    runGetVersionSeriesList({
      distribution: props.releaseVersion!.id,
    });
  };

  watch(
    () => props.releaseVersion,
    () => {
      if (props.releaseVersion) {
        fetchVersionSeriesList();
        return;
      }
    },
    {
      immediate: true,
    },
  );

  const handleAddVersionSuccess = () => {
    fetchVersionSeriesList();
    emits('refreshReleaseList');
  };

  const handleTableListChange = (count: number) => {
    dbVersionListCount.value = count;
  };

  const handleSearchChange = (value: Record<string, any>) => {
    const filterValue = _.cloneDeep(value);
    Object.keys(value).forEach((key) => {
      if (key === 'enable') {
        if (value[key].includes(',')) {
          filterValue[key] = filterValue[key].split(',').map((item: string) => item === 'true');
        } else {
          filterValue[key] = [filterValue[key] === 'true'];
        }
      } else {
        filterValue[key] = filterValue[key].trim();
      }
    });
    subVersionRefs.value?.setFilterValue(value);
  };

  const handleFilterValueChange = (value: Record<string, any>) => {
    const filterValue = _.cloneDeep(value);

    Object.keys(filterValue).forEach((key) => {
      const itemValue = filterValue[key];
      if (Array.isArray(itemValue)) {
        filterValue[key] = itemValue.map(String).join(',');
      } else {
        filterValue[key] = itemValue.trim();
      }
    });
    searchValue.value = filterValue;
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
    const index = versionSeriesList.value!.findIndex((item) => item.id === versionSeriesId);
    if (index !== -1) {
      subVersionRefs.value!.refresh();
      emits('refreshReleaseList');
    } else {
      emits('refreshReleaseList');
      fetchVersionSeriesList();
    }
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
