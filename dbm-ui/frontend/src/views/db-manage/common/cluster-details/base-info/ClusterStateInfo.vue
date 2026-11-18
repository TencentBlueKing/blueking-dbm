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

<!-- 基本信息 Tab 分为「集群信息」「运行概况」两组：默认插槽放原有基本信息，下方完整展示运行概况字段 -->
<template>
  <div
    ref="root"
    class="cluster-detail-state-info">
    <div class="cluster-detail-group-title">{{ t('集群信息') }}</div>
    <slot />
    <div
      ref="clusterStateTitle"
      class="cluster-detail-group-title">
      {{ t('运行概况') }}
    </div>
    <!-- 字段定义返回后再渲染，InfoList 挂载时才能按同组最宽对齐标签 -->
    <InfoList v-if="displayFields.length > 0">
      <InfoItem
        v-for="field in displayFields"
        :key="field.key"
        :label="field.name">
        {{ getClusterStateDisplay(data.states, field.key) }}
      </InfoItem>
    </InfoList>
  </div>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { ClusterStateValue } from '@services/types';

  import { getClusterStateDisplay, useClusterStateSchema, useUrlSearch } from '@hooks';

  import type { ClusterTypes } from '@common/const';

  import { CLUSTER_DETAIL_ANCHOR_CLUSTER_STATE, URL_CLUSTER_DETAIL_ANCHOR_KEY } from '../constants';

  import InfoList, { InfoItem } from './components/Index.vue';

  interface Props {
    clusterType: ClusterTypes.TENDBCLUSTER | ClusterTypes.TENDBHA | ClusterTypes.TENDBSINGLE;
    data: {
      states: Record<string, ClusterStateValue>;
    };
  }

  interface Slots {
    default: () => VNode;
  }

  const props = defineProps<Props>();
  defineSlots<Slots>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { removeSearchParam } = useUrlSearch();

  const { displayFields } = useClusterStateSchema(props.clusterType);

  const rootRef = useTemplateRef('root');
  const clusterStateTitleRef = useTemplateRef('clusterStateTitle');

  // 定位后跟随内容高度变化的最长时间
  const FOLLOW_DURATION = 3000;
  // 用户主动滚动时停止跟随
  const USER_SCROLL_EVENTS = ['wheel', 'touchmove', 'keydown', 'mousedown'] as const;

  let stopFollow: (() => void) | undefined;

  const scrollToClusterState = () => {
    clusterStateTitleRef.value?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  };

  // 集群信息里的 CLB、从域名等子块是异步加载的，加载后会把运行概况往下推：
  // 在一段时间内监听整体高度变化并重新定位，超时或用户主动滚动后停止
  const followClusterState = () => {
    if (!rootRef.value) {
      return;
    }
    stopFollow?.();
    // observe 时会立即回调一次，完成首次定位
    const observer = new ResizeObserver(scrollToClusterState);
    observer.observe(rootRef.value);
    const stop = () => {
      observer.disconnect();
      clearTimeout(timer);
      USER_SCROLL_EVENTS.forEach((name) => window.removeEventListener(name, stop, true));
      stopFollow = undefined;
    };
    const timer = setTimeout(stop, FOLLOW_DURATION);
    USER_SCROLL_EVENTS.forEach((name) => window.addEventListener(name, stop, true));
    stopFollow = stop;
  };

  // 从「查看全部 N 项」进入时 URL 带锚点：字段渲染完成后定位到运行概况分组，并清掉锚点，避免切 Tab、刷新时重复定位
  watch(
    [() => route.query[URL_CLUSTER_DETAIL_ANCHOR_KEY], () => displayFields.value.length > 0],
    ([anchor, isFieldsReady]) => {
      if (anchor !== CLUSTER_DETAIL_ANCHOR_CLUSTER_STATE || !isFieldsReady) {
        return;
      }
      router.replace({
        query: removeSearchParam(URL_CLUSTER_DETAIL_ANCHOR_KEY, false),
      });
      nextTick(followClusterState);
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    stopFollow?.();
  });
</script>
<style lang="less">
  .cluster-detail-state-info {
    .cluster-detail-group-title {
      padding-top: 20px;
      font-size: 12px;
      font-weight: 700;
      line-height: 20px;
      color: #313238;
    }
  }
</style>
