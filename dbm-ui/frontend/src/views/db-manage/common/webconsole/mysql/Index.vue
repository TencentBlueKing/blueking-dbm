<template>
  <div
    ref="rootRef"
    class="mysql-webconsole">
    <div class="top-main">
      <ClusterTabs
        ref="clusterTabsRef"
        :before-close="handleBeforeClose"
        :db-type="dbType"
        @change="handleChangeCurrentCluster"
        @closed="handleCloseTab" />
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
      <div
        v-if="!clusterInfo"
        class="placeholder-main">
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
      <template v-else-if="currentTab">
        <div class="content-top">
          <div class="content-top-start ml-14">
            <div
              v-bk-tooltips="parametersLocked ? t('WebConsole_执行或连接期间不可修改参数') : t('WebConsole_修改参数重建会话')">
              <div
                class="session-parameters"
                :class="{ 'session-parameters-locked': parametersLocked }">
                <RoleSelect
                  v-model="connectionMode"
                  class="session-mode-select"
                  :list="connectionModeList" />
                <RoleSelect
                  v-model="role"
                  :list="roleList" />
                <TimeZone
                  v-if="currentTab.mode === 'http'"
                  v-model="timezone" />
                <span
                  v-else
                  class="session-default-timezone">
                  {{ t('WebConsole_服务端默认时区') }}
                </span>
                <CharacterSet v-model="charset" />
              </div>
            </div>
            <template v-if="currentTab.mode === 'ws'">
              <span
                v-bk-tooltips="currentTab.error || t('WebConsole_重连不会恢复数据库上下文')"
                class="session-status">
                {{ connectionStateText }}
              </span>
              <BkButton
                v-if="currentTab.state === 'disconnected' || currentTab.state === 'closed'"
                class="session-reconnect"
                size="small"
                text
                theme="primary"
                @click="handleReconnect">
                {{ t('WebConsole_重新连接') }}
              </BkButton>
            </template>
          </div>
          <div class="content-top-end">
            <div
              v-bk-tooltips="currentTab.busy ? t('WebConsole_执行期间不可清屏') : ''"
              :class="{ 'session-parameters-locked': currentTab.busy }">
              <ClearScreen @change="handleClickClearScreen" />
            </div>
            <ExportData @export="handleClickExport" />
          </div>
        </div>
        <KeepAlive
          v-for="tab in tabs"
          :key="tab.key">
          <ConsolePanel
            v-if="clusterInfo && currentTab.key === tab.key"
            :key="tab.key"
            :ref="handleConsolePanelRef"
            :charset="tab.charset"
            :cluster="clusterInfo"
            :disabled="tab.mode === 'ws' && tab.state !== 'ready'"
            :execute-command="tab.mode === 'ws' ? tab.execute : undefined"
            :role="tab.role"
            :style="currentFontConfig"
            :timezone="tab.timezone"
            @loading-change="tab.setBusy" />
        </KeepAlive>
      </template>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { InfoBox } from 'bkui-vue';
  import screenfull from 'screenfull';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { WebconsoleOptions } from '@services/source/webconsoleWs';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { releaseConsoleTab } from '@views/db-manage/common/webconsole/components/console-panel/components/ConsoleInput.vue';
  import { useWebconsoleSession } from '@views/db-manage/common/webconsole/hooks/useWebconsoleSession';

  import CharacterSet from '../components/CharacterSet.vue';
  import ClearScreen from '../components/ClearScreen.vue';
  import ClusterTabs, { type ClusterItem } from '../components/ClusterTabs.vue';
  import ConsolePanel from '../components/console-panel/mysql/Index.vue';
  import ExportData from '../components/ExportData.vue';
  import FontSetting from '../components/FontSetting.vue';
  import FullScreen from '../components/FullScreen.vue';
  import RoleSelect from '../components/RoleSelect.vue';
  import TimeZone from '../components/time-zone/Index.vue';
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
  const { connect, ensureTab, removeTab, setMode, tabs } = useWebconsoleSession();
  const currentTab = computed(() => (clusterInfo.value ? tabs[clusterInfo.value.id] : undefined));
  const modeChanging = ref(false);
  const parametersLocked = computed(
    () =>
      modeChanging.value ||
      Boolean(currentTab.value?.busy) ||
      currentTab.value?.state === 'connecting' ||
      currentTab.value?.state === 'initializing',
  );
  const role = computed<WebconsoleOptions['role']>({
    get: () => currentTab.value?.role || 'backend_slave',
    set: (value) => {
      const tab = currentTab.value;
      if (!tab || parametersLocked.value || tab.role === value) {
        return;
      }
      tab.role = value;
      if (tab.mode === 'ws' && clusterInfo.value) {
        connect(clusterInfo.value.id);
      }
    },
  });
  const charset = computed({
    get: () => currentTab.value?.charset || 'default',
    set: (value: string) => {
      const tab = currentTab.value;
      if (!tab || parametersLocked.value || tab.charset === value) {
        return;
      }
      tab.charset = value;
      if (tab.mode === 'ws' && clusterInfo.value) {
        connect(clusterInfo.value.id);
      }
    },
  });
  const timezone = computed({
    get: () => currentTab.value?.timezone || '+08:00',
    set: (value: string) => {
      if (currentTab.value && !parametersLocked.value) {
        currentTab.value.timezone = value;
      }
    },
  });
  const connectionModeList = [
    { label: 'HTTP', value: 'http' },
    { label: 'WebSocket', value: 'ws' },
  ];
  const connectionMode = computed({
    get: () => currentTab.value?.mode || 'http',
    set: (value: string) => {
      const tab = currentTab.value;
      const clusterId = clusterInfo.value?.id;
      if (!tab || !clusterId || parametersLocked.value || value === tab.mode || (value !== 'http' && value !== 'ws')) {
        return;
      }
      modeChanging.value = true;
      InfoBox({
        cancelText: t('取消'),
        confirmText: t('确定'),
        content: t(value === 'ws' ? 'WebConsole_切换WS确认' : 'WebConsole_切换HTTP确认'),
        onCancel() {
          modeChanging.value = false;
        },
        onConfirm() {
          if (tabs[clusterId] === tab) {
            setMode(clusterId, value);
          }
          modeChanging.value = false;
        },
        title: t('WebConsole_切换连接方式'),
      });
    },
  });
  const connectionStateText = computed(() => {
    const labels = {
      closed: t('WebConsole_未连接'),
      connecting: t('WebConsole_连接中'),
      disconnected: t('WebConsole_已断开'),
      executing: t('WebConsole_执行中'),
      initializing: t('WebConsole_初始化中'),
      ready: t('WebConsole_已连接'),
    };
    return currentTab.value ? labels[currentTab.value.state] : '';
  });
  const isFullScreen = ref(false);
  const showUsageHelp = ref(false);

  /**
   *- MySQL 主从：可选master 、slave  ；默认连接slave （对应 standy从实例）
    - MySQL 单节点：连接 orphan ，不可选
   */
  const roleListConfig = {
    [ClusterTypes.TENDBHA]: [
      { label: 'Master', value: 'backend_master' },
      { label: 'Slave', value: 'backend_slave' },
    ],
    [ClusterTypes.TENDBSINGLE]: [{ label: 'Orphan', value: 'orphan' }],
  };

  const roleList = ref<ComponentProps<typeof RoleSelect>['list']>([]);

  const handleBeforeClose = (clusterId: number) =>
    new Promise<boolean>((resolve, reject) => {
      const isInputed = tabs[clusterId]?.busy || consolePanelRef.value?.isInputed(clusterId);
      if (isInputed) {
        InfoBox({
          cancelText: t('取消'),
          confirmText: t('关闭'),
          content: t(tabs[clusterId]?.busy ? 'WebConsole_关闭执行中会话确认' : '关闭后，内容将不会再在保存，请谨慎操作！'),
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

  const handleConsolePanelRef = (instance: unknown) => {
    if (instance) {
      consolePanelRef.value = instance as InstanceType<typeof ConsolePanel>;
    }
  };

  const handleShowClustersPanel = () => {
    clusterTabsRef.value!.showClustersPanel();
  };

  const handleClickClearScreen = () => {
    if (clusterInfo.value && !currentTab.value?.busy) {
      consolePanelRef.value?.clearCurrentScreen(clusterInfo.value.id);
    }
  };

  const handleCloseTab = (clusterId: number) => {
    removeTab(clusterId);
    releaseConsoleTab(clusterId);
  };

  const handleReconnect = () => {
    if (clusterInfo.value && !parametersLocked.value) {
      connect(clusterInfo.value.id);
    }
  };

  const handleClickExport = () => {
    consolePanelRef.value!.export();
  };

  const handleChangeCurrentCluster = (data: ClusterItem | undefined) => {
    clusterInfo.value = data;
    if (!data) {
      return;
    }
    roleList.value = roleListConfig[data.cluster_type as keyof typeof roleListConfig];
    ensureTab(data.id, data.cluster_type === ClusterTypes.TENDBSINGLE ? 'orphan' : 'backend_slave');
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
    Object.keys(tabs).forEach((id) => releaseConsoleTab(Number(id)));
  });
</script>
<style lang="less">
  .mysql-webconsole {
    display: flex;
    height: calc(100% - 24px);
    font-size: 12px;
    color: #c4c6cc;
    background: #1a1a1a;
    transform: translate(0, 0);
    flex-direction: column;

    .top-main {
      display: flex;
      height: 40px;
      background: #2e2e2e;
      box-shadow: 0 2px 4px 0 #00000029;

      .use-help-selected {
        color: #699df4;
        background: #242424;
      }

      .using-help-wrap {
        position: fixed;
        top: 40px;
        right: 0;
        z-index: 99;
        height: calc(100% - 40px);
        background: transparent;
      }
    }

    .content-main {
      position: relative;
      flex: 1;

      .content-top {
        position: absolute;
        z-index: 10;
        display: flex;
        width: 100%;
        height: 32px;
        background: #242424;
        box-shadow: 0 2px 4px 0 #00000029;
        align-items: center;
        justify-content: space-between;

        .content-top-start {
          display: flex;
          min-width: 0;
          align-items: center;
        }

        .session-parameters {
          display: flex;
          align-items: center;
        }

        .session-mode-select .role-select-trigger {
          width: 96px;
        }

        .session-default-timezone,
        .session-status {
          margin: 0 8px;
          white-space: nowrap;
        }

        .session-reconnect {
          margin-right: 8px;
        }

        .content-top-end {
          display: flex;
        }
      }

      .console-panel-main {
        position: absolute;
        top: 32px;
        z-index: 1;
        height: calc(100% - 32px);
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

    .session-parameters-locked {
      pointer-events: none;
      opacity: 0.5;
    }

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
  }
</style>
