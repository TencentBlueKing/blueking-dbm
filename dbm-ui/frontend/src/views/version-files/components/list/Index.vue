<template>
  <div class="list-main">
    <ReleaseVersionList
      v-if="dbType === DBTypes.MYSQL"
      :key="renderKey"
      ref="releaseVersionListRef"
      :db-type="dbType"
      :pkg-label-map="pkgLabelMap"
      :pkg-type="pkgType"
      @choose-release="handleChooseRelease"
      @release-list-count-change="handleReleaseListCountChange" />
    <SubVersionList
      ref="subVersionListRef"
      :db-type="dbType"
      :pkg-label-map="pkgLabelMap"
      :pkg-type="pkgType"
      :release-version="activeReleaseVersion"
      @refresh-release-list="handleRefreshReleaseList" />
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { getReleaseVersionList } from '@services/source/version';

  import { DBTypes } from '@common/const';

  import type { TabItem } from '../../Index.vue';

  import ReleaseVersionList from './components/release-version-list/Index.vue';
  import SubVersionList from './components/sub-version-list/Index.vue';

  interface Props {
    dbType: string;
    pkgLabelMap: Record<string, string>;
    pkgType: string;
    tabs: TabItem[];
  }

  const props = defineProps<Props>();

  const releaseVersionListRef = ref<InstanceType<typeof ReleaseVersionList>>();
  const subVersionListRef = ref<InstanceType<typeof SubVersionList>>();
  const activeReleaseVersion = ref<ReleaseVersionModel>();

  const renderKey = computed(() => `${props.dbType}-${props.pkgType}`);

  const { run: runGetReleaseList } = useRequest(getReleaseVersionList, {
    manual: true,
    onSuccess(data) {
      activeReleaseVersion.value = data[0];
    },
  });

  watch(
    () => [props.dbType, props.pkgType],
    () => {
      activeReleaseVersion.value = undefined;
      if (props.dbType !== 'mysql') {
        const pkgList = props.tabs.find((item) => item.name === props.dbType)?.children.map((item) => item.name);
        if (pkgList?.includes(props.pkgType)) {
          runGetReleaseList({
            db_type: props.dbType,
            pkg_type: props.pkgType,
          });
        }
      }
      setTimeout(() => {
        releaseVersionListRef.value?.refresh();
      });
    },
    {
      immediate: true,
    },
  );

  const handleReleaseListCountChange = (count: number) => {
    subVersionListRef.value!.showReleaseEmpty(count === 0);
  };

  const handleChooseRelease = (data: ReleaseVersionModel) => {
    activeReleaseVersion.value = data;
  };

  const handleRefreshReleaseList = () => {
    releaseVersionListRef.value?.refresh();
  };
</script>
<style lang="less">
  .list-main {
    display: flex;
    height: 100%;
    padding: 16px;
    overflow: hidden;
  }
</style>
