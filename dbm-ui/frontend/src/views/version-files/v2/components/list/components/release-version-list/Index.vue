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
  <div class="release-version-list-main">
    <div class="title-operate">
      <div class="title">{{ t('发行版') }}</div>
      <AuthTemplate
        action-id="package_manage"
        :permission="hasPackageManagePermission"
        :resource="dbType">
        <DbIcon
          v-bk-tooltips="t('新增发行版')"
          class="add-icon"
          type="add"
          @click="() => handleEditRelease(false)" />
      </AuthTemplate>
    </div>
    <div class="release-list">
      <ScrollFaker ref="scrollFakerRef">
        <div
          v-for="(item, index) in releaseList"
          :key="item.name"
          class="release-item"
          :class="{ 'is-active': activeReleaseIndex === index }"
          @click="() => handleChooseRelease(index)">
          <div class="name">{{ item.name }}</div>
          <div class="count">{{ item.dbversion_count }}</div>
          <div class="item-operate">
            <AuthTemplate
              action-id="package_manage"
              :permission="item.permission.package_manage"
              :resource="dbType">
              <DbIcon
                v-bk-tooltips="t('编辑')"
                class="edit-icon mr-8"
                type="edit"
                @click.stop="() => handleEditRelease(true, item)" />
            </AuthTemplate>
            <DeleteRelease
              :data="item"
              :db-type="dbType"
              :pkg-type="pkgType"
              @success="fetchReleaseList" />
          </div>
        </div>
      </ScrollFaker>
    </div>
  </div>
  <EditRelease
    v-model:is-show="isShowEditRelease"
    :data="currentRelease"
    :db-type="dbType"
    :existed-name-list="existedReleaseNames"
    :is-edit="isEditRelease"
    :pkg-type="pkgType"
    :tag-label="pkgLabelMap[pkgType] || '--'"
    @success="handleSuccess" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getReleaseVersionList } from '@services/source/version';

  import ScrollFaker from '@components/scroll-faker/Index.vue';

  import DeleteRelease from './components/DeleteRelease.vue';
  import EditRelease from './components/EditRelease.vue';

  interface Props {
    dbType: string;
    hasPackageManagePermission: boolean;
    pkgLabelMap: Record<string, string>;
    pkgType: string;
  }

  interface Emits {
    (e: 'releaseListCountChange', count: number): void;
    (e: 'chooseRelease', data?: ReleaseItem): void;
  }

  interface Exposes {
    refresh: () => void;
  }

  type ReleaseItem = ServiceReturnType<typeof getReleaseVersionList>[number];

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { locale, t } = useI18n();

  const VERSION_FILES_RELEASE_LIST_ACTIVE_INDEX = 'VERSION_FILES_RELEASE_LIST_ACTIVE_INDEX';

  const scrollFakerRef = useTemplateRef('scrollFakerRef');
  const isShowEditRelease = ref(false);
  const isEditRelease = ref(false);
  const activeReleaseIndex = ref(0);
  const currentRelease = ref<ReleaseItem>();
  const releaseList = ref<ReleaseItem[]>([]);

  const existedReleaseNames = computed(() => releaseList.value.map((item) => item.name.toLowerCase()));

  // 新增发行版后需要把列表滚回顶部
  let shouldScrollToTop = false;

  /** 缓存内容可能来自旧版本或被手工改坏，读写都不能让页面挂掉 */
  const readMemoryIndex = () => {
    try {
      const cacheStr = localStorage.getItem(VERSION_FILES_RELEASE_LIST_ACTIVE_INDEX);
      if (!cacheStr) {
        return 0;
      }
      const index = Number(JSON.parse(cacheStr)?.[props.dbType]?.[props.pkgType]);
      return Number.isInteger(index) && index > 0 ? index : 0;
    } catch {
      return 0;
    }
  };

  const writeMemoryIndex = (index: number) => {
    let cache: Record<string, Record<string, number>> = {};
    try {
      cache = JSON.parse(localStorage.getItem(VERSION_FILES_RELEASE_LIST_ACTIVE_INDEX) || '{}') || {};
    } catch {
      cache = {};
    }
    Object.assign(cache, {
      [props.dbType]: {
        ...cache[props.dbType],
        [props.pkgType]: index,
      },
    });
    localStorage.setItem(VERSION_FILES_RELEASE_LIST_ACTIVE_INDEX, JSON.stringify(cache));
  };

  const { run: runGetReleaseVersionList } = useRequest(getReleaseVersionList, {
    manual: true,
    onSuccess(data) {
      releaseList.value = data.sort((a, b) =>
        a.name.localeCompare(b.name, locale.value, {
          numeric: true,
          sensitivity: 'base',
        }),
      );
      emits('releaseListCountChange', data.length);
      if (shouldScrollToTop) {
        shouldScrollToTop = false;
        nextTick(() => {
          scrollFakerRef.value?.scrollTo(0, 0);
        });
      }
    },
  });

  const fetchReleaseList = () => {
    runGetReleaseVersionList({
      db_type: props.dbType,
      pkg_type: props.pkgType,
    });
  };

  watch(
    () => [activeReleaseIndex.value, releaseList.value],
    () => {
      if (releaseList.value.length === 0) {
        emits('chooseRelease', undefined);
        return;
      }
      // 发行版被删除后记忆下标可能越界，先收敛到最后一项再对外抛出
      if (activeReleaseIndex.value > releaseList.value.length - 1) {
        activeReleaseIndex.value = releaseList.value.length - 1;
        return;
      }
      emits('chooseRelease', releaseList.value[activeReleaseIndex.value]);
    },
    {
      immediate: true,
    },
  );

  const handleSuccess = () => {
    shouldScrollToTop = !isEditRelease.value;
    fetchReleaseList();
  };

  const handleChooseRelease = (index: number) => {
    activeReleaseIndex.value = index;
    writeMemoryIndex(index);
  };

  const handleEditRelease = (isEdit: boolean, data?: ReleaseItem) => {
    isShowEditRelease.value = true;
    isEditRelease.value = isEdit;
    currentRelease.value = data;
  };

  onMounted(() => {
    activeReleaseIndex.value = readMemoryIndex();
    fetchReleaseList();
  });

  defineExpose<Exposes>({
    refresh: () => {
      fetchReleaseList();
    },
  });
</script>

<style lang="less">
  .release-version-list-main {
    display: flex;
    height: 100%;
    min-width: 260px;
    background: #f5f7fa;
    border-radius: 2px;
    flex-direction: column;

    .title-operate {
      display: flex;
      padding: 16px;
      align-items: center;
      justify-content: space-between;

      .title {
        font-size: 14px;
        font-weight: 700;
        color: #4d4f56;
      }

      .add-icon {
        color: #979ba5;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .release-list {
      flex: 1;
      overflow-y: auto;

      .release-item {
        display: flex;
        height: 40px;
        padding: 0 16px;
        color: #4d4f56;
        cursor: pointer;
        border-radius: 2px;
        align-items: center;
        justify-content: space-between;

        &:hover {
          background: #eaebf0;

          .item-operate {
            display: block;
          }

          .count {
            display: none;
          }
        }

        &.is-active {
          background: #e1ecff;

          .name {
            color: #3a84ff;
          }

          .count {
            color: #fff;
            background: #a3c5fd;
          }
        }

        .name {
          font-size: 14px;
        }

        .count {
          height: 16px;
          padding: 0 6px;
          font-size: 12px;
          color: #979ba5;
          background: #f0f1f5;
          border-radius: 2px;
        }

        .item-operate {
          display: none;
          color: #c4c6cc;

          .edit-icon {
            color: #979ba5;

            &:hover {
              color: #3a84ff;
            }

            &.is-disabled {
              color: #c4c6cc;
              cursor: not-allowed;
            }
          }
        }
      }
    }
  }
</style>
