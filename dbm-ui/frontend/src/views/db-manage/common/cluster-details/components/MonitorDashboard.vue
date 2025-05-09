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
  <BkLoading :loading="isLoading">
    <div
      ref="monitorRef"
      class="cluster-detail-monitor-dashboard-box">
      <div
        class="action-box"
        @click.stop>
        <i
          v-bk-tooltips="screenIcon.text"
          class="action-btn"
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
        style="display: flex; border: 1px solid #24292e1f">
        <iframe :src="url" />
      </div>
    </div>
  </BkLoading>
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

  const { t } = useI18n();

  const monitorRef = ref<HTMLIFrameElement>();
  const iframeContainerRef = useTemplateRef('iframeContainer');

  const { isFullscreen, toggle } = useFullscreen(monitorRef);

  const isLoading = ref(false);
  const offsettop = ref('0px');

  const screenIcon = computed(() => ({
    icon: isFullscreen.value ? 'db-icon-un-full-screen' : 'db-icon-full-screen',
    text: isFullscreen.value ? t('取消全屏') : t('全屏'),
  }));

  onMounted(() => {
    setTimeout(() => {
      offsettop.value = `${iframeContainerRef.value?.getBoundingClientRect().top || 0}px`;
    });
  });
</script>

<style lang="less">
  .cluster-detail-monitor-dashboard-box {
    padding: 14px 0;
    background-color: white;

    .action-box {
      display: flex;
      padding-bottom: 16px;
    }

    .action-btn {
      margin-left: 16px;
      margin-left: auto;
      font-size: @font-size-large;
      text-align: center;
      cursor: pointer;

      &:hover {
        color: @primary-color;
      }
    }

    iframe {
      width: 100%;
      min-height: calc(100vh - v-bind(offsettop) - 20px);
      border: 0;
    }
  }
</style>
