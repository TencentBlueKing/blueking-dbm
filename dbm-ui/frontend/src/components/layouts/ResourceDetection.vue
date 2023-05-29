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
  <BkDialog
    v-model:is-show="state.isShow"
    class="resource-update-dialog"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    header-align="center"
    height="auto"
    :quick-close="false"
    theme="warning"
    :title="$t('资源更新提醒')"
    :width="400"
    @closed="handleCancelReload"
    @confirm="handleConfirmReload">
    <p class="resource-update-dialog__content">
      {{ $t('服务器端资源文件已经更新_请刷新页面获取最新资源_以免前端页面执行失败_造成困扰') }}
    </p>
    <p class="resource-update-dialog__warning">
      {{ $t('点击确定将刷新页面_请注意保存数据') }}
    </p>
  </BkDialog>
</template>
<script lang="ts">
  import { useTimeoutPoll } from '@vueuse/core';

  export default {
    name: 'ResourceDetection',
  };
</script>

<script setup lang="ts">

  const state = reactive({
    isShow: false,
    isCancel: false,
  });
  const isProd = import.meta.env.MODE === 'production';

  // get url
  const { VITE_PUBLIC_PATH } = window.PROJECT_ENV;
  const base = `${window.location.origin}${VITE_PUBLIC_PATH ? VITE_PUBLIC_PATH : '/'}`;
  let url = '';
  try {
    url = new URL(__RESOURCE_UNIQUE_KEY__, base).href;
  } catch (e) {
    console.error(e);
  }

  /**
   * 轮询资源更新情况
   */
  const fetchStaticResource = () => {
    fetch(url)
      .then((res) => {
        if (res.status === 404 && !state.isCancel) {
          state.isShow = true;
        }
      });
  };
  const { pause, resume } = useTimeoutPoll(fetchStaticResource, 3000);
  onMounted(() => {
    if (isProd) {
      url && resume();
    }
  });

  /**
   * 确认刷新获取最新资源
   */
  const handleConfirmReload = () => {
    state.isShow = false;
    window.location.reload();
  };

  /**
   * 取消刷新
   */
  const handleCancelReload = () => {
    pause();
    state.isShow = false;
    state.isCancel = true;
  };
</script>

<style lang="less" scoped>
  .resource-update-dialog {
    text-align: center;

    &__warning {
      margin: 16px 0 24px;
      font-weight: bold;
      color: @danger-color;
      text-align: center;
    }
  }
</style>
