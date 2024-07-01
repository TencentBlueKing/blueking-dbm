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
              v-overflow-tips
              class="cluster-name"
              >{{ clustersMap[clusterId].immute_domain }}</span
            >
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
            @mouseenter="handleHoverAddIcon" />
        </div>
      </div>
      <TopOperation
        ref="topOperationRef"
        v-model:isFullScreen="isFullScreen"
        v-model:showUseageHelp="showUseageHelp"
        @clear-current-screen="handleClickClearScreen"
        @export="handleClickExport"
        @font-size-change="handleChangeFontSize"
        @toggle-full-screen="handleClickFullScreen"
        @toggle-show-help="handleToggleHelp" />
    </div>
    <div class="content-main">
      <div
        v-show="showUseageHelp"
        class="using-help-wrap">
        <UseingHelp @hide="handleHideUseingHelp" />
      </div>
      <ConsolePanel
        v-if="activeClusterId > 0"
        ref="consolePanelRef"
        :cluster-info="clustersMap[activeClusterId]"
        :cluster-type="clusterType"
        :font-config="currentFontConfig" />
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
          filterable
          :model-value="currentCluster"
          multiple
          :popover-options="{ disableTeleport: true }"
          @change="handleClusterSelectChange">
          <template #trigger>
            <span></span>
          </template>
          <BkOption
            v-for="(item, index) in clusterList"
            :key="index"
            :name="item.immute_domain"
            :value="item.id" />
        </BkSelect>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import screenfull from 'screenfull';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { messageWarn } from '@utils';

  import ConsolePanel from './components/console-panel/Index.vue';
  import TopOperation from './components/TopOperation.vue';
  import UseingHelp from './components/useingHelp.vue';

  export interface Props {
    clusterType?: 'mysql' | 'tendbcluster' | 'redis';
  }

  export type ClusterItem = ServiceReturnType<typeof queryAllTypeCluster>[number];

  const props = withDefaults(defineProps<Props>(), {
    clusterType: 'mysql',
  });

  const { t } = useI18n();

  const rootRef = ref();
  const consolePanelRef = ref<InstanceType<typeof ConsolePanel>>();
  const clutersRef = ref();
  const currentCluster = ref<number[]>([]);
  const selectedClusters = ref<number[]>([]);
  const activeClusterId = ref(0);
  const showUseageHelp = ref(false);
  const addTabRef = ref();
  const popRef = ref();
  const currentFontConfig = ref({
    fontSize: '12px',
    lineHeight: '20px',
  });
  const isFullScreen = ref(false);
  const clustersMap = ref<Record<number, ClusterItem>>({});
  const topOperationRef = ref();

  const clustersPanelHeight = computed(() => {
    if (!clusterList.value) {
      return '120px';
    }

    if (clusterList.value.length >= 6) {
      return `300px`;
    }
    const height = 300 - (6 - clusterList.value.length) * 32;
    return `${height}px`;
  });

  const queryClusterTypesMap = {
    mysql: 'tendbha,tendbsingle',
    tendbcluster: 'tendbcluster',
    redis: 'redis',
  };
  let clustersRaw: ClusterItem[] = [];
  let tippyIns: Instance | undefined;

  const { data: clusterList } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_types: queryClusterTypesMap[props.clusterType],
        phase: 'online',
      },
    ],
    onSuccess(data) {
      clustersMap.value = data.reduce(
        (results, item) => {
          Object.assign(results, {
            [item.id]: item,
          });
          return results;
        },
        {} as Record<number, ClusterItem>,
      );
      clustersRaw = data;
    },
  });

  const handleShowClustersSelect = () => {
    tippyIns?.show();
  };

  const handleCloseTab = (index: number) => {
    const currentClusterId = selectedClusters.value[index];
    consolePanelRef.value!.clearCurrentScreen(currentClusterId);
    selectedClusters.value.splice(index, 1);
    const clusterCount = selectedClusters.value.length;
    if (currentClusterId === activeClusterId.value) {
      // 关闭当前打开tab
      activeClusterId.value = clusterCount === 0 ? 0 : selectedClusters.value[clusterCount - 1];
    }
    currentCluster.value = [];
    updateClusterSelect();
  };

  const handleActiveTab = (id: number) => {
    activeClusterId.value = id;
  };

  const handleHoverAddIcon = () => {
    handleShowClustersSelect();
    setTimeout(() => {
      clutersRef.value.showPopover();
    });
  };

  const handleClusterSelectChange = (ids: number[]) => {
    if (selectedClusters.value.length === 8) {
      messageWarn(t('页签数量已达上限，请先关闭部分标'));
      currentCluster.value = [];
      return;
    }

    let id = 0;
    if (ids.length > 1) {
      id = ids.pop()!;
      selectedClusters.value.push(id);
      currentCluster.value = [id];
    } else {
      currentCluster.value = ids;
      [id] = ids;
      selectedClusters.value.push(id);
    }

    if (activeClusterId.value === 0) {
      activeClusterId.value = id;
    }

    updateClusterSelect();
    tippyIns?.hide();
  };

  const updateClusterSelect = () => {
    clusterList.value = clustersRaw.filter((item) => !selectedClusters.value.includes(item.id));
  };

  const handleClickClearScreen = () => {
    consolePanelRef.value!.clearCurrentScreen();
  };

  const handleToggleHelp = () => {
    showUseageHelp.value = !showUseageHelp.value;
  };

  const handleHideUseingHelp = () => {
    showUseageHelp.value = false;
  };

  const handleChangeFontSize = (item: { fontSize: string; lineHeight: string }) => {
    currentFontConfig.value = item;
  };

  const handleClickFullScreen = () => {
    screenfull.toggle(rootRef.value);
    isFullScreen.value = !isFullScreen.value;
  };

  const handleClickExport = () => {
    consolePanelRef.value!.export();
  };

  const checkFullScreen = () => {
    isFullScreen.value = screenfull.isFullscreen;
  };

  onMounted(() => {
    screenfull.on('change', checkFullScreen);

    tippyIns = tippy(addTabRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-start',
      appendTo: rootRef.value,
      theme: 'light',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: true,
      offset: [0, 0],
      zIndex: 999999,
      hideOnClick: true,
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
        box-shadow: none;
      }
    }

    .webconsole-select-clusters {
      width: 388px;
      background: #fff;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      box-shadow: 0 2px 6px 0 #0000001a;

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
    height: 900px;
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
              box-shadow: none;
            }
          }
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
    }
  }
</style>
