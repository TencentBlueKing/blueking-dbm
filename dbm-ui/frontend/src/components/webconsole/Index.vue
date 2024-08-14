<template>
  <div
    ref="rootRef"
    class="webconsole-main">
    <div class="top-main">
      <div class="tabs-main">
        <div
          v-for="(clusterId, index) in selectedClusters"
          :key="clusterId"
          class="tab-item"
          :class="{ 'item-selected': clusterId === activeClusterId }"
          @click="() => handleActiveTab(clusterId)">
          <div class="active-bar"></div>
          <div class="tab-item-content">
            <span
              v-bk-tooltips="clustersMap[clusterId]?.immute_domain"
              class="cluster-name">
              {{ clustersMap[clusterId]?.immute_domain }}
            </span>
            <div
              class="icon-main"
              @click.stop="() => handleCloseTab(index)">
              <DbIcon
                class="hover-close-icon-1"
                type="close" />
              <DbIcon
                class="hover-close-icon-2"
                type="close-circle-shape" />
            </div>
          </div>
        </div>
        <div
          ref="addTabRef"
          class="add-icon-main">
          <DbIcon
            class="add-icon"
            type="increase"
            @click="handleClickAddIcon" />
        </div>
      </div>
      <div class="top-operate-main">
        <RawSwitcher
          v-if="configMap[dbType]?.showRawSwitcher"
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
        v-if="activeClusterId > 0"
        ref="consolePanelRef"
        :cluster-info="clustersMap[activeClusterId]"
        :db-type="dbType"
        :font-config="currentFontConfig"
        :operable-params="operableParams" />
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
    <div style="display: none">
      <div
        ref="popRef"
        class="webconsole-select-clusters"
        :style="{ height: clustersPanelHeight }">
        <div class="title">{{ t('连接的集群') }}</div>
        <BkSelect
          ref="clutersRef"
          class="clusters-select"
          disable-focus-behavior
          filterable
          :model-value="selectedClusters"
          multiple
          :popover-options="{ disableTeleport: true }"
          @change="handleClusterSelectChange">
          <template #trigger>
            <span></span>
          </template>
          <BkOption
            v-for="item in clusterList"
            :key="item.id"
            :name="item.immute_domain"
            :value="item.id" />
        </BkSelect>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { InfoBox } from 'bkui-vue';
  import screenfull from 'screenfull';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  import { messageWarn } from '@utils';

  import ClearScreen from './components/ClearScreen.vue';
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

  interface WebConsoleConfig {
    // 数据库下所有集群类型
    clusterTypes: string;
    // 是否展示raw模式开关
    showRawSwitcher?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const { t } = useI18n();
  const route = useRoute();

  const rootRef = ref();
  const consolePanelRef = ref<InstanceType<typeof ConsolePanel>>();
  const clutersRef = ref();
  const selectedClusters = ref<number[]>([]);
  const activeClusterId = ref(0);
  const addTabRef = ref();
  const popRef = ref();
  const currentFontConfig = ref({
    fontSize: '12px',
    lineHeight: '20px',
  });
  const clustersMap = ref<Record<number, ClusterItem>>({});
  const topOperateState = reactive({
    isRaw: false,
    isFullScreen: false,
    showUseageHelp: false,
  });

  const operableParams = computed(() => {
    let parmas = {};
    if (configMap[props.dbType]?.showRawSwitcher) {
      parmas = {
        ...parmas,
        raw: topOperateState.isRaw,
      };
    }
    return parmas;
  });
  const clustersPanelHeight = computed(() => {
    if (!clusterList.value) {
      return '120px';
    }

    if (clusterList.value.length >= 6) {
      return `288px`;
    }

    const height = 288 - (6 - clusterList.value.length) * 32;
    return `${height}px`;
  });

  const routeClusterId = route.query.clusterId;
  let clustersRaw: ClusterItem[] = [];
  let tippyIns: Instance | undefined;
  const configMap: { [key in DBTypes]?: WebConsoleConfig } = {
    [DBTypes.MYSQL]: {
      clusterTypes: 'tendbha,tendbsingle',
    },
    [DBTypes.TENDBCLUSTER]: {
      clusterTypes: 'tendbcluster',
    },
    [DBTypes.REDIS]: {
      clusterTypes: 'TwemproxyRedisInstance,PredixyTendisplusCluster,TwemproxyTendisSSDInstance,PredixyRedisCluster',
      showRawSwitcher: true,
    },
  };

  const { data: clusterList } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_types: configMap[props.dbType]?.clusterTypes,
        phase: 'online',
      },
    ],
    onSuccess(data) {
      clustersMap.value = data.reduce<Record<number, ClusterItem>>((results, item) => {
        Object.assign(results, {
          [item.id]: item,
        });
        return results;
      }, {});
      clustersRaw = data;

      if (routeClusterId) {
        const clusterId = Number(routeClusterId);
        setTimeout(() => {
          handleClusterSelectChange([clusterId]);
        });
      }
    },
  });

  const removeTab = (index: number) => {
    const currentClusterId = selectedClusters.value[index];
    consolePanelRef.value?.clearCurrentScreen(currentClusterId);
    selectedClusters.value.splice(index, 1);
    const clusterCount = selectedClusters.value.length;
    if (currentClusterId === activeClusterId.value) {
      // 关闭当前打开tab
      activeClusterId.value = clusterCount === 0 ? 0 : selectedClusters.value[clusterCount - 1];
    }
    updateClusterSelect();
  };

  const handleCloseTab = (index: number) => {
    const currentClusterId = selectedClusters.value[index];
    const isInputed = consolePanelRef.value?.isInputed(currentClusterId);
    if (isInputed) {
      InfoBox({
        title: t('确认关闭当前窗口？'),
        content: t('关闭后，内容将不会再在保存，请谨慎操作！'),
        headerAlign: 'center',
        footerAlign: 'center',
        confirmText: t('关闭'),
        cancelText: t('取消'),
        onConfirm() {
          removeTab(index);
        },
      });
    } else {
      removeTab(index);
    }
  };

  const handleActiveTab = (id: number) => {
    activeClusterId.value = id;
  };

  const handleShowClustersPanel = () => {
    tippyIns?.show();
  };

  const handleClickAddIcon = () => {
    setTimeout(() => {
      clutersRef.value.showPopover();
    });
  };

  const handleClusterSelectChange = (ids: number[]) => {
    if (ids.length === 0) {
      return;
    }

    if (selectedClusters.value.length === 8) {
      messageWarn(t('页签数量已达上限，请先关闭部分标'));
      return;
    }

    const id = ids.pop()!;
    selectedClusters.value.push(id);
    activeClusterId.value = id;
    updateClusterSelect();
    tippyIns?.hide();
  };

  const updateClusterSelect = () => {
    clusterList.value = clustersRaw.filter((item) => !selectedClusters.value.includes(item.id));
  };

  const handleClickRawSwitcher = (value: boolean) => {
    topOperateState.isRaw = value;
  };

  const handleClickClearScreen = () => {
    consolePanelRef.value?.clearCurrentScreen();
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

  const handleClickExport = () => {
    consolePanelRef.value?.export();
  };

  const checkFullScreen = () => {
    topOperateState.isFullScreen = screenfull.isFullscreen;
  };

  onMounted(() => {
    screenfull.on('change', checkFullScreen);

    tippyIns = tippy(addTabRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-start',
      appendTo: rootRef.value,
      theme: 'light',
      maxWidth: 'none',
      trigger: 'mouseenter click',
      interactive: true,
      arrow: true,
      offset: [0, 0],
      zIndex: 999999,
      hideOnClick: true,
      onShow() {
        setTimeout(() => {
          clutersRef.value.showPopover();
        });
      },
      onHide() {
        clutersRef.value.hidePopover();
      },
    });
  });

  onBeforeUnmount(() => {
    screenfull.off('change', checkFullScreen);

    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>
<style lang="less">
  .tippy-content {
    padding: 0 !important;

    .clusters-select {
      .bk-select-popover {
        border: none;
        transform: translate3d(0, 41px, 0);
        box-shadow: none;
      }
    }

    .webconsole-select-clusters {
      width: 388px;

      .title {
        height: 40px;
        margin: 4px 8px 0;
        font-weight: 700;
        line-height: 40px;
        color: #313238;
        border-bottom: 1px solid #eaebf0;
      }
    }
  }

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

      .tabs-main {
        flex: 1;
        display: flex;
        overflow: hidden;

        .tab-item {
          position: relative;
          width: 200px;
          height: 40px;
          min-width: 60px;
          line-height: 40px;
          color: #c4c6cc;
          text-align: center;
          cursor: pointer;
          background: #2e2e2e;
          box-shadow: 0 2px 4px 0 #00000029;
          align-items: center;

          &::after {
            position: absolute;
            top: 12px;
            right: 0;
            width: 1px;
            height: 16px;
            background: #63656e;
            content: '';
          }

          &.item-selected {
            background: #242424;

            .active-bar {
              background: #3a84ff;
            }
          }

          .active-bar {
            width: 100%;
            height: 3px;
          }

          .tab-item-content {
            display: flex;
            width: 100%;
            padding: 0 15px 0 24px;
            align-items: center;

            .cluster-name {
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              flex: 1;
            }

            .icon-main {
              display: flex;
              width: 35px;
              justify-content: flex-end;

              &:hover {
                .hover-close-icon-2 {
                  display: block;
                }

                .hover-close-icon-1 {
                  display: none;
                }
              }

              .hover-close-icon-1 {
                font-size: 20px;
                color: #979ba5;
              }

              .hover-close-icon-2 {
                display: none;
                font-size: 24px;
                color: #63656e;
              }
            }
          }
        }

        .add-icon-main {
          position: relative;
          display: flex;
          margin-left: 13px;
          cursor: pointer;
          align-items: center;

          &:hover {
            .add-icon {
              color: #eaebf0;
            }
          }

          .add-icon {
            font-size: 15px;
            color: #c4c6cc;
          }

          .clusters-select {
            .bk-select-popover {
              border: none;
              transform: translate3d(0, 41px, 0);
              box-shadow: none;
            }
          }
        }
      }

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
          // gap: 15px;

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
