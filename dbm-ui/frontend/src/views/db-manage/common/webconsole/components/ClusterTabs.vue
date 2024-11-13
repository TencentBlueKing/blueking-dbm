<template>
  <div class="tabs-main">
    <div
      v-for="(clusterId, index) in selectedClusters"
      :key="clusterId"
      class="tab-item"
      :class="{ 'item-selected': clusterId === modelValue }"
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
</template>

<script setup lang="ts">
  import type { Instance, SingleTarget } from 'tippy.js';
  import tippy from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { DBTypes, queryClusterTypes } from '@common/const';

  import { messageWarn } from '@utils';

  export type ClusterItem = ServiceReturnType<typeof queryAllTypeCluster>[number];

  interface Props {
    dbType: DBTypes;
    beforeClose: (clusterId: number) => Promise<boolean>;
  }

  interface Emits {
    (e: 'change', data: ClusterItem): void;
    (e: 'removeTab', clusterId: number): void;
  }

  interface Exposes {
    showClustersPanel(): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();

  const modelValue = defineModel({
    default: 0 as number,
    type: Number,
  });

  const routeClusterId = route.query.clusterId;
  let clustersRaw: ClusterItem[] = [];
  let tippyIns: Instance | undefined;

  const clutersRef = ref();
  const addTabRef = ref();
  const popRef = ref();
  const clustersMap = ref<Record<number, ClusterItem>>({});
  const selectedClusters = ref<number[]>([]);

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

  const { data: clusterList } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_types: queryClusterTypes[props.dbType].join(','),
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
    modelValue.value = id;
    emits('change', clustersMap.value[id]);
    updateClusterSelect();
    tippyIns?.hide();
  };

  const updateClusterSelect = () => {
    clusterList.value = clustersRaw.filter((item) => !selectedClusters.value.includes(item.id));
  };

  const handleActiveTab = (id: number) => {
    modelValue.value = id;
    emits('change', clustersMap.value[id]);
  };

  const handleCloseTab = async (index: number) => {
    const currentClusterId = selectedClusters.value[index];
    const isClose = await props.beforeClose(currentClusterId);
    if (isClose) {
      removeTab(index);
    }
  };

  const removeTab = (index: number) => {
    const currentClusterId = selectedClusters.value[index];
    selectedClusters.value.splice(index, 1);
    const clusterCount = selectedClusters.value.length;
    if (currentClusterId === modelValue.value) {
      emits('removeTab', currentClusterId);
      // 关闭当前打开tab
      modelValue.value = clusterCount === 0 ? 0 : selectedClusters.value[clusterCount - 1];
      emits('change', clustersMap.value[modelValue.value]);
    }
    updateClusterSelect();
  };

  const handleClickAddIcon = () => {
    setTimeout(() => {
      clutersRef.value.showPopover();
    });
  };

  onMounted(() => {
    tippyIns = tippy(addTabRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-start',
      appendTo: () => document.body,
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
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  defineExpose<Exposes>({
    showClustersPanel() {
      tippyIns?.show();
    },
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

  .tabs-main {
    display: flex;
    margin-right: auto;
    overflow: hidden;
    flex: 1;

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
</style>
