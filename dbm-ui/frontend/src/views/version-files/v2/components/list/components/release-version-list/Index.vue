<template>
  <div class="release-version-list-main">
    <div class="title-operate">
      <div class="title">{{ t('发行版') }}</div>
      <DbIcon
        v-bk-tooltips="t('新增发行版')"
        class="add-icon"
        type="add"
        @click="() => handleEditRelease(false)" />
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
            <DbIcon
              v-bk-tooltips="t('编辑')"
              class="edit-icon mr-8"
              type="edit"
              @click.stop="() => handleEditRelease(true, item)" />
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
    pkgLabelMap: Record<string, string>;
    pkgType: string;
  }

  interface Emits {
    (e: 'releaseListCountChange', count: number): void;
    (e: 'chooseRelease', data: ReleaseItem): void;
  }

  interface Exposes {
    refresh: () => void;
  }

  type ReleaseItem = ServiceReturnType<typeof getReleaseVersionList>[number];

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const scrollFakerRef = useTemplateRef('scrollFakerRef');
  const isShowEditRelease = ref(false);
  const isEditRelease = ref(false);
  const activeReleaseIndex = ref(0);
  const currentRelease = ref<ReleaseItem>();

  const { data: releaseList, run: runGetReleaseVersionList } = useRequest(getReleaseVersionList, {
    manual: true,
    onSuccess(data) {
      emits('releaseListCountChange', data.length);
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
      if (releaseList.value && releaseList.value.length > 0) {
        emits('chooseRelease', releaseList.value[activeReleaseIndex.value]);
      }
    },
    {
      immediate: true,
    },
  );

  const handleSuccess = () => {
    fetchReleaseList();
    if (!isEditRelease.value) {
      setTimeout(() => {
        scrollFakerRef.value?.scrollTo(0, 0);
      }, 500);
    }
  };

  const handleChooseRelease = (index: number) => {
    activeReleaseIndex.value = index;
  };

  const handleEditRelease = (isEdit: boolean, data?: ReleaseItem) => {
    isShowEditRelease.value = true;
    isEditRelease.value = isEdit;
    currentRelease.value = data;
  };

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
