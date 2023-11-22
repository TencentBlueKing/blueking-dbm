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

<template>
  <div
    ref="monitorRef"
    class="cluster-monitor">
    <BkLoading
      :loading="isLoading"
      style="height: 100%;">
      <div
        class="cluster-monitor-bar"
        @click.stop>
        <i
          v-bk-tooltips="screenIcon.text"
          class="cluster-monitor-bar__icon"
          :class="[screenIcon.icon]"
          @click.stop="toggle" />
      </div>
      <BkException
        v-if="url === '#'"
        class="exception-wrap-item"
        :description="$t('监控组件初始化中_紧急情况请联系平台管理员')"
        type="building" />
      <iframe
        v-else
        :src="url" />
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  // import { getMonitorUrl } from '@services/common';
  // import { useGlobalBizs } from '@stores';
  import { useFullscreen } from '@vueuse/core';

  interface Props {
    url?: string,

  }

  withDefaults(defineProps<Props>(), {
    url: '',
  });

  const monitorRef = ref<HTMLIFrameElement>();
  const { t } = useI18n();
  // const { currentBizId } = useGlobalBizs();
  const { isFullscreen, toggle } = useFullscreen(monitorRef);

  const isLoading = ref(false);
  // const link = ref('');

  // const targetUrl = computed(() => (props.url ? props.url : link.value));

  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  // const fetchLink = (id: number) => {
  //   if (props.url || !props.clusterType || !props.id) return;

  //   isLoading.value = true;
  //   const fetchKey = props.isFetchInstance ? 'instance_id' : 'cluster_id';
  //   getMonitorUrl({
  //     bk_biz_id: currentBizId,
  //     cluster_type: props.clusterType,
  //     [fetchKey]: id,
  //   })
  //     .then((res) => {
  //       link.value = res.url;
  //     })
  //     .finally(() => {
  //       isLoading.value = false;
  //     });
  // };

  // watch([() => props.id, () => props.clusterType], () => {
  //   if (props.id && props.clusterType) {
  //     fetchLink(props.id);
  //   }
  // }, { immediate: true });
</script>

<style lang="less" scoped>
.cluster-monitor {
  width: 100%;
  height: 100%;
  padding: 14px 0;
  background-color: white;

  &-bar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-bottom: 16px;

    &__icon {
      display: block;
      margin-left: 16px;
      font-size: @font-size-large;
      text-align: center;
      cursor: pointer;

      &:hover {
        color: @primary-color;
      }
    }
  }

  iframe {
    width: 100%;
    height: calc(100% - 30px);
    border: 0;
  }
}
</style>
