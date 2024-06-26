<template>
  <div
    ref="rootRef"
    class="webconsole-main">
    <div class="top-main">
      <div class="tabs-main">
        <div
          class="tab-item"
          :class="{ 'item-selected': clusterId === activeClusterId }"
          v-for="(clusterId, index) in selectedClusters"
          :key="clusterId"
          @click="() => handleActiveTab(clusterId)">
          <div class="active-bar"></div>
          <div class="tab-item-content">
            <span
              class="cluster-name"
              v-overflow-tips>{{ clustersMap[clusterId].immute_domain }}</span>
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
        <div class="add-icon-main" ref="addTabRef">
          <DbIcon
            class="add-icon"
            type="increase"
            @mouseenter="handleHoverAddIcon" />
        </div>
      </div>
      <div class="operate-main">
        <div
          class="operate-item"
          @click="handleClickClearScreen">
          <div class="operate-item-inner">
            <DbIcon
              class="operate-icon"
              type="clearing" />
            <span class="operate-title">{{ t('清屏') }}</span>
          </div>
          
        </div>
        <div class="operate-item">
          <div
            class="operate-item-inner"
            @click="handleClickExport">
            <DbIcon
              class="operate-icon"
              type="daochu" />
            <span class="operate-title">{{ t('导出') }}</span>
          </div>
        </div>
        <div
          class="operate-item"
          :class="{'use-help-selected': showUseageHelp}"
          @click="handleToggleHelp">
          <div class="operate-item-inner">
            <DbIcon
              class="operate-icon"
              type="help-fill" />
            <span class="operate-title">{{ t('使用帮助') }}</span>
          </div>
        </div>
        <div class="operate-item-last">
          <BkPopover
            placement="bottom"
            extCls="font-change-popover"
            theme="dark">
            <div
              v-bk-tooltips="t('字号调整')"
              class="operate-icon">
              <div class="operate-icon-inner">
                <DbIcon
                  type="aa" />
              </div>
            </div>
            <template #content>
              <div class="font-change-main">
                <div
                  class="font-item"
                  :class="{'font-item-active': item === currentFontSize}"
                  v-for="item in fontSizeList" :key="item"
                  @click="() => handleChangeFontSize(item)">
                  <DbIcon
                    :style="{'font-size': item }"
                    type="aa" />
                </div>
              </div>
            </template>
          </BkPopover>
          <div class="operate-icon">
            <div
              class="operate-icon-inner"
              @click="handleClickFullScreen">
              <DbIcon
                class="operate-icon"
                :type="isFullScreen ? 'un-full-screen' : 'full-screen'" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="content-main">
      <div
        class="using-help-wrap"
        v-show="showUseageHelp">
        <UseingHelp @hide="handleHideUseingHelp" />
      </div>
      <ConsolePanel
        ref="consolePanelRef"
        :clusterType="clusterType"
        :fontSize="currentFontSize"
        v-if="activeClusterId > 0"
        :clusterInfo="clustersMap[activeClusterId]" />
    </div>
    <div style="display: none;">
      <div
        ref="popRef"
        class="webconsole-select-clusters"
        :style="{height: clustersPanelHeight}">
        <div class="title">{{ t('连接的集群') }}</div>
        <BkSelect
          ref="clutersRef"
          :model-value="currentCluster"
          multiple
          class="clusters-select"
          :popover-options="{ disableTeleport: true }"
          filterable
          @change="handleClusterSelectChange">
          <template #trigger>
            <span></span>
          </template>
          <BkOption
            v-for="(item, index) in clusterList"
            :value="item.id"
            :key="index"
            :name="item.immute_domain" />
        </BkSelect>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { queryAllTypeCluster } from '@services/dbbase';
  import { useRequest } from 'vue-request';
  import ConsolePanel from './components/console-panel/Index.vue';
  import UseingHelp from './components/useingHelp.vue';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { messageWarn } from '@utils';
  import screenfull from 'screenfull';

  export interface Props {
    clusterType?: 'mysql' | 'tendbcluster' | 'redis'
  }
  
  export type ClusterItem = ServiceReturnType<typeof queryAllTypeCluster>[number];

  const props = withDefaults(defineProps<Props>(), {
    clusterType: 'mysql'
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
  const currentFontSize = ref('12px');
  const isFullScreen = ref(false);
  const clustersMap = ref<Record<number, ClusterItem>>({});

  const clustersPanelHeight = computed(() => {
    if (!clusterList.value) {
      return '120px';
    }

    if (clusterList.value.length >= 6) {
      return `300px`;
    } else {
      const height = 300 -  (6 - clusterList.value.length) * 32;
      return `${height}px`;
    }
  });

  const queryClusterTypesMap = {
    mysql: 'tendbha,tendbsingle',
    tendbcluster: 'tendbcluster',
    redis: 'redis',
  }
  const fontSizeList = ['12px', '14px', '16px']
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
    }
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
  }

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
      return 
    }

    let id = 0;
    if (ids.length > 1) {
      id = ids.pop()!;
      selectedClusters.value.push(id);
      currentCluster.value = [id];
    } else {
      currentCluster.value = ids;
      [id] = ids
      selectedClusters.value.push(id);
    }

    if (activeClusterId.value === 0) {
      activeClusterId.value = id;
    }
    
    updateClusterSelect();
    tippyIns?.hide();
  };

  const updateClusterSelect = () => {
    clusterList.value = clustersRaw.filter(item => !selectedClusters.value.includes(item.id));
  }

  const handleClickClearScreen = () => {
    consolePanelRef.value!.clearCurrentScreen();
  }

  const handleToggleHelp = () => {
    showUseageHelp.value = !showUseageHelp.value;
  }

  const handleHideUseingHelp = () => {
    showUseageHelp.value = false;
  }

  const handleChangeFontSize = (size: string) => {
    currentFontSize.value = size;
  }

  const handleClickFullScreen = () => {
    screenfull.toggle(rootRef.value);
    isFullScreen.value = !isFullScreen.value;
  }

  const handleClickExport = () => {
    consolePanelRef.value!.export();
  }

  onMounted(() => {
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
  })

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  })
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
      background: #ffffff;
      border: 1px solid #dcdee5;
      box-shadow: 0 2px 6px 0 #0000001a;
      border-radius: 2px;

      .title {
        height: 40px;
        line-height: 40px;
        font-weight: 700;
        color: #313238;
        margin: 4px 8px 0;
        border-bottom: 1px solid #eaebf0;
      }
    }
  }
  

  .webconsole-main {
    width: 100%;
    height: 900px;
    background: #1a1a1a;
    display: flex;
    flex-direction: column;

    .top-main {
      width: 100%;
      height: 40px;
      background: #2e2e2e;
      box-shadow: 0 2px 4px 0 #00000029;
      display: flex;
      justify-content: space-between;
      font-size: 12px;

      .tabs-main {
        flex: 1;
        display: flex;
        overflow: hidden;

        .tab-item {
          position: relative;
          align-items: center;
          min-width: 60px;
          width: 200px;
          height: 40px;
          background: #2e2e2e;
          box-shadow: 0 2px 4px 0 #00000029;
          line-height: 40px;
          text-align: center;
          color: #c4c6cc;
          cursor: pointer;

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
            width: 100%;
            display: flex;
            align-items: center;
            padding: 0 15px 0 24px;

            .cluster-name {
              flex: 1;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }

            .icon-main {
              width: 35px;
              display: flex;
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
                color: #979ba5;
                font-size: 20px;
              }

              .hover-close-icon-2 {
                display: none;
                color: #63656e;
                font-size: 24px;
              }
            }
          }
        }

        .add-icon-main {
          display: flex;
          align-items: center;
          margin-left: 13px;
          cursor: pointer;
          position: relative;

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

      .operate-main {
        color: #c4c6cc;
        display: flex;
        min-width: 300px;

        .operate-item {
          position: relative;
          height: 40px;
          padding: 0 7px;
          display: flex;
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
            padding: 0 6px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;

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
          height: 40px;
          display: flex;
          align-items: center;
          padding: 0 6px;
          cursor: pointer;
          // gap: 15px;

          .operate-icon {
            height: 40px;
            font-size: 16px;
            display: flex;
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
          background: #242424;
          color: #699DF4;
        }
      }
    }

    .content-main {
      flex: 1;
      overflow: hidden;
      position: relative;

      .using-help-wrap {
        position: absolute;
        width: 100%;
        height: 100%;
        background: transparent
      }
    }
  }

  .font-change-popover {
    padding: 0 !important;

    .font-change-main {
      display: flex;
      padding: 2px;
      background: #2E2E2E;
      border: 1px solid #3D3D3D;
      box-shadow: 0 2px 6px 0 #0000001f;
      border-radius: 2px;
      cursor: pointer;

      .font-item{
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #979BA5;
      }

      .font-item-active {
        background: #424242;
        border-radius: 1px;
        color: #DCDEE5;
      }
    }
  }
  
</style>
