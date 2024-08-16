<template>
  <div
    ref="rootRef"
    class="webconsole-main">
    <div class="top-main">
      <ClusterTabs
        ref="clusterTabsRef"
        :db-type="dbType"
        :is-inputed="isInputed"
        @before-close="handleClickClearScreen"
        @change="handleChangeCurrentCluster" />
      <div class="top-operate-main">
        <RawSwitcher
          v-if="dbType === DBTypes.REDIS"
          v-model="topOperateState.isRaw"
          :db-type="dbType"
          @change="handleClickRawSwitcher" />
        <ClearScreen @clear-current-screen="handleClickClearScreen" />
        <ExportData @export="handleClickExport" />
        <UseHelp
          v-model:showUseageHelp="topOperateState.showUseageHelp"
          @toggle-show-help="handleToggleHelp" />
        <div class="operate-item-last">
          <FontChange @font-size-change="handleChangeFontSize" />
          <FullScreen
            v-model:isFullScreen="topOperateState.isFullScreen"
            @toggle-full-screen="handleClickFullScreen" />
        </div>
      </div>
    </div>
    <div class="content-main">
      <div
        v-show="topOperateState.showUseageHelp"
        class="using-help-wrap">
        <UsingHelpPanel
          :db-type="dbType"
          @hide="handleHideUsingHelp" />
      </div>
      <ConsolePanel
        v-if="clusterInfo"
        ref="consolePanelRef"
        :cluster-info="clusterInfo"
        :db-type="dbType"
        :raw="topOperateState.isRaw"
        :style="currentFontConfig" />
      <div class="placeholder-main">
        <DbIcon
          class="warn-icon"
          type="attention" />
        <span>{{ t('请先添加链接的集群') }}，</span>
        <BkButton
          text
          theme="primary"
          @click="handleShowClustersPanel">
          {{ t('立即添加') }}
        </BkButton>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import screenfull from 'screenfull';
  import { useI18n } from 'vue-i18n';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  import ClearScreen from './components/ClearScreen.vue';
  import ClusterTabs from './components/ClusterTabs.vue';
  import ConsolePanel from './components/console-panel/Index.vue';
  import ExportData from './components/ExportData.vue';
  import FontChange from './components/FontChange.vue';
  import FullScreen from './components/FullScreen.vue';
  import RawSwitcher from './components/RawSwitcher.vue';
  import UseHelp from './components/UseHelp.vue';
  import UsingHelpPanel from './components/using-help-panel/Index.vue';

  export interface Props {
    dbType?: DBTypes;
  }

  export type ClusterItem = ServiceReturnType<typeof queryAllTypeCluster>[number];

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const { t } = useI18n();

  const rootRef = ref();
  const clusterTabsRef = ref();
  const consolePanelRef = ref<InstanceType<typeof ConsolePanel>>();
  const clusterInfo = ref<ClusterItem>();
  const currentFontConfig = ref({
    fontSize: '12px',
    lineHeight: '20px',
  });
  const topOperateState = reactive({
    isRaw: props.dbType === DBTypes.REDIS ? false : undefined,
    isFullScreen: false,
    showUseageHelp: false,
  });

  const isInputed = (clusterId: number) => consolePanelRef.value!.isInputed(clusterId);

  const handleShowClustersPanel = () => {
    clusterTabsRef.value!.showClustersPanel();
  };

  const handleClickClearScreen = (clusterId?: number) => {
    consolePanelRef.value!.clearCurrentScreen(clusterId as number);
  };

  const handleClickExport = () => {
    consolePanelRef.value!.export();
  };

  const handleChangeCurrentCluster = (data: ClusterItem) => {
    clusterInfo.value = data;
  };

  const handleClickRawSwitcher = (value?: boolean) => {
    topOperateState.isRaw = value;
  };

  const handleToggleHelp = () => {
    topOperateState.showUseageHelp = !topOperateState.showUseageHelp;
  };

  const handleHideUsingHelp = () => {
    topOperateState.showUseageHelp = false;
  };

  const handleChangeFontSize = (item: { fontSize: string; lineHeight: string }) => {
    currentFontConfig.value = item;
  };

  const handleClickFullScreen = () => {
    screenfull.toggle(rootRef.value);
    topOperateState.isFullScreen = !topOperateState.isFullScreen;
  };

  const checkFullScreen = () => {
    topOperateState.isFullScreen = screenfull.isFullscreen;
  };

  onMounted(() => {
    screenfull.on('change', checkFullScreen);
  });

  onBeforeUnmount(() => {
    screenfull.off('change', checkFullScreen);
  });
</script>
<style lang="less">
  .webconsole-main {
    display: flex;
    width: 100%;
    height: 100%;
    background: #1a1a1a;
    flex-direction: column;

    .top-main {
      display: flex;
      width: 100%;
      height: 40px;
      font-size: 12px;
      background: #2e2e2e;
      box-shadow: 0 2px 4px 0 #00000029;
      justify-content: space-between;

      .top-operate-main {
        display: flex;
        min-width: 300px;
        color: #c4c6cc;

        .operate-item {
          position: relative;
          display: flex;
          height: 40px;
          padding: 0 7px;
          align-items: center;

          &::after {
            position: absolute;
            top: 12px;
            right: 0;
            width: 1px;
            height: 16px;
            background: #45464d;
            content: '';
          }

          .operate-item-inner {
            display: flex;
            height: 28px;
            padding: 0 6px;
            cursor: pointer;
            align-items: center;
            justify-content: center;

            &:hover {
              background: #424242;
              border-radius: 2px;
            }

            .operate-icon {
              font-size: 16px;
            }

            .operate-title {
              margin-left: 5px;
            }
          }
        }

        .operate-item-last {
          display: flex;
          height: 40px;
          padding: 0 6px;
          cursor: pointer;
          align-items: center;

          .operate-icon {
            display: flex;
            height: 40px;
            font-size: 16px;
            align-items: center;

            .operate-icon-inner {
              display: flex;
              align-items: center;
              justify-content: center;
              width: 28px;
              height: 28px;

              &:hover {
                background: #424242;
                border-radius: 2px;
              }
            }
          }
        }

        .use-help-selected {
          color: #699df4;
          background: #242424;
        }
      }
    }

    .content-main {
      position: relative;
      overflow: hidden;
      flex: 1;

      .using-help-wrap {
        position: absolute;
        width: 100%;
        height: 100%;
        background: transparent;
      }

      .placeholder-main {
        display: flex;
        width: 100%;
        height: 100%;
        font-size: 14px;
        color: #c4c6cc;
        justify-content: center;
        align-items: center;

        .warn-icon {
          margin-top: 3px;
          margin-right: 8px;
        }
      }
    }
  }
</style>
