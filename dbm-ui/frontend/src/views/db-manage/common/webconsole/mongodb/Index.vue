<template>
  <div
    ref="rootRef"
    class="mongodb-webconsole">
    <div class="top-main">
      <ClusterTabs
        ref="clusterTabsRef"
        :before-close="handleBeforeClose"
        :db-type="dbType"
        @change="handleChangeCurrentCluster"
        @remove-tab="handleClickClearScreen" />
      <ClearScreen @change="handleClickClearScreen" />
      <ExportData @export="handleClickExport" />
      <UsageHelp
        v-model="showUsageHelp"
        :db-type="dbType" />
      <div class="operate-item-last">
        <FontSetting
          v-model="currentFontConfig"
          @change="handleChangeFontSize" />
        <FullScreen
          v-model="isFullScreen"
          @change="handleClickFullScreen" />
      </div>
    </div>
    <div class="content-main">
      <KeepAlive>
        <ConsolePanel
          v-if="clusterInfo"
          :key="clusterInfo.id"
          ref="consolePanelRef"
          :cluster="clusterInfo"
          :style="currentFontConfig" />
      </KeepAlive>
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
  import { InfoBox } from 'bkui-vue';
  import screenfull from 'screenfull';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import ClearScreen from '../components/ClearScreen.vue';
  import ClusterTabs, { type ClusterItem } from '../components/ClusterTabs.vue';
  import ConsolePanel from '../components/console-panel/mongodb/Index.vue';
  import ExportData from '../components/ExportData.vue';
  import FontSetting from '../components/FontSetting.vue';
  import FullScreen from '../components/FullScreen.vue';
  import UsageHelp from '../components/usage-help/Index.vue';

  interface Props {
    dbType: DBTypes;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const rootRef = ref();
  const clusterTabsRef = ref();
  const consolePanelRef = ref<InstanceType<typeof ConsolePanel>>();
  const clusterInfo = ref<ClusterItem>();
  const currentFontConfig = ref({
    fontSize: '12px',
    lineHeight: '20px',
  });
  const isFullScreen = ref(false);
  const showUsageHelp = ref(false);

  const handleBeforeClose = (clusterId: number) =>
    new Promise<boolean>((resolve, reject) => {
      const isInputed = consolePanelRef.value!.isInputed(clusterId);
      if (isInputed) {
        InfoBox({
          cancelText: t('取消'),
          confirmText: t('关闭'),
          content: t('关闭后，内容将不会再在保存，请谨慎操作！'),
          footerAlign: 'center',
          headerAlign: 'center',
          onCancel() {
            reject(false);
          },
          onConfirm() {
            resolve(true);
          },
          title: t('确认关闭当前窗口？'),
        });
      } else {
        resolve(true);
      }
    });

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

  const handleChangeFontSize = (item: { fontSize: string; lineHeight: string }) => {
    currentFontConfig.value = item;
  };

  const handleClickFullScreen = () => {
    screenfull.toggle(rootRef.value);
    isFullScreen.value = !isFullScreen.value;
  };

  const checkFullScreen = () => {
    isFullScreen.value = screenfull.isFullscreen;
  };

  onMounted(() => {
    screenfull.on('change', checkFullScreen);
  });

  onBeforeUnmount(() => {
    screenfull.off('change', checkFullScreen);
  });
</script>
<style lang="less">
  .mongodb-webconsole {
    font-size: 12px;
    color: #c4c6cc;
    background: #1a1a1a;
    height: calc(100% - 24px);
    display: flex;
    flex-direction: column;
    transform: translate(0, 0);

    .top-main {
      display: flex;
      height: 40px;
      background: #2e2e2e;
      box-shadow: 0 2px 4px 0 #00000029;

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

      .using-help-wrap {
        position: fixed;
        top: 40px;
        z-index: 99;
        height: calc(100% - 40px);
        background: transparent;
      }
    }

    .content-main {
      position: relative;
      overflow: hidden;
      flex: 1;

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
