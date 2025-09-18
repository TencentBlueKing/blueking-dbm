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
    class="dbm-cluster-monitor">
    <BkLoading
      :loading="isLoading"
      style="height: 100%">
      <div
        class="dbm-cluster-monitor-bar"
        @click.stop>
        <i
          v-bk-tooltips="screenIcon.text"
          class="dbm-cluster-monitor-btn"
          :class="[screenIcon.icon]"
          @click.stop="toggle" />
      </div>
      <BkException
        v-if="url === '#'"
        class="exception-wrap-item"
        :description="$t('监控组件初始化中_紧急情况请联系平台管理员')"
        type="building" />
      <div
        v-else
        ref="iframeContainer"
        class="monitor-page">
        <div class="iframe-page-navigation-mask" />
        <iframe
          :src="url"
          @load="handleLoad" />
      </div>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useFullscreen } from '@vueuse/core';

  interface Props {
    url?: string;
  }

  withDefaults(defineProps<Props>(), {
    url: '',
  });

  const monitorRef = ref<HTMLIFrameElement>();
  const iframeContainerRef = useTemplateRef('iframeContainer');
  const { t } = useI18n();
  const { isFullscreen, toggle } = useFullscreen(monitorRef);

  const isLoading = ref(true);

  const offsettop = ref('0px');

  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  watch(isFullscreen, (val) => {
    if (val) {
      offsettop.value = '46px';
    } else {
      setTimeout(() => {
        offsettop.value = `${iframeContainerRef.value?.getBoundingClientRect().top || 0}px`;
      });
    }
  });

  onMounted(() => {
    setTimeout(() => {
      offsettop.value = `${iframeContainerRef.value?.getBoundingClientRect().top || 0}px`;
    });
  });

  const handleLoad = () => {
    isLoading.value = false;
  };
</script>

<style lang="less">
  .dbm-cluster-monitor {
    width: 100%;
    height: 100%;
    padding: 14px 0;
    background-color: white;

    .dbm-cluster-monitor-bar {
      display: flex;
      padding-right: 16px;
      padding-bottom: 16px;
      align-items: center;
      justify-content: flex-end;
    }

    .dbm-cluster-monitor-btn {
      display: block;
      margin-left: 16px;
      font-size: @font-size-large;
      text-align: center;
      cursor: pointer;

      &:hover {
        color: @primary-color;
      }
    }

    .monitor-page {
      position: relative;
      display: flex;
      border: 1px solid #24292e1f;
      border-top: none;
    }

    .iframe-page-navigation-mask {
      position: absolute;
      top: 1px;
      left: 1px;
      width: calc(100% - 400px);
      height: 50px;
      background-color: transparent;
    }

    iframe {
      width: 100%;
      min-height: calc(100vh - v-bind(offsettop) - 20px);
      border: 0;
    }
  }
</style>
