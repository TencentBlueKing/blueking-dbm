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
  <div class="version-file-list-box">
    <ReleaseVersionList
      v-if="isPureMysql"
      :key="renderKey"
      ref="releaseVersionListRef"
      :db-type="dbType"
      :has-package-manage-permission="hasPackageManagePermission"
      :pkg-label-map="pkgLabelMap"
      :pkg-type="pkgType"
      @choose-release="handleChooseRelease"
      @release-list-count-change="handleReleaseListCountChange" />
    <SubVersionList
      :key="renderKey"
      ref="subVersionListRef"
      :db-type="dbType"
      :has-package-manage-permission="hasPackageManagePermission"
      :pkg-type="pkgType"
      :release-version="activeReleaseVersion"
      :version-num="versionNum"
      @refresh-release-list="handleRefreshReleaseList" />
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { getReleaseVersionList } from '@services/source/version';

  import { isPureMysqlPkgType } from '@views/version-files/v2/common';

  import ReleaseVersionList from './components/release-version-list/Index.vue';
  import SubVersionList from './components/sub-version-list/Index.vue';

  interface Props {
    dbType: string;
    hasPackageManagePermission: boolean;
    pkgLabelMap: Record<string, string>;
    pkgType: string;
    versionNum: number;
  }

  type Emits = (e: 'refreshPkgTypeList') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const releaseVersionListRef = ref<InstanceType<typeof ReleaseVersionList>>();
  const subVersionListRef = ref<InstanceType<typeof SubVersionList>>();
  const activeReleaseVersion = ref<ReleaseVersionModel>();

  const renderKey = computed(() => `${props.dbType}-${props.pkgType}`);
  const isPureMysql = computed(() => isPureMysqlPkgType(props.dbType, props.pkgType));

  const { run: runGetReleaseList } = useRequest(getReleaseVersionList, {
    manual: true,
    onSuccess(data) {
      activeReleaseVersion.value = data[0];
    },
  });

  watch(
    [() => props.dbType, () => props.pkgType],
    () => {
      activeReleaseVersion.value = undefined;
      // 纯 mysql 的发行版由左侧列表自己拉取，并通过 chooseRelease 回传选中项
      if (isPureMysql.value) {
        return;
      }
      runGetReleaseList({
        db_type: props.dbType,
        pkg_type: props.pkgType,
      });
    },
    {
      immediate: true,
    },
  );

  const handleReleaseListCountChange = (count: number) => {
    subVersionListRef.value?.showReleaseEmpty(count === 0);
  };

  const handleChooseRelease = (data?: ReleaseVersionModel) => {
    activeReleaseVersion.value = data;
    subVersionListRef.value?.clearFilter();
  };

  const handleRefreshReleaseList = () => {
    releaseVersionListRef.value?.refresh();
    emits('refreshPkgTypeList');
  };
</script>
<style lang="less">
  .version-file-list-box {
    display: flex;
    height: 100%;
    padding: 16px;
    overflow: hidden;
  }
</style>
