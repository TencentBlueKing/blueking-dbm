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
    v-if="state.isShow"
    class="login-modal">
    <div
      class="login-modal__container"
      :style="styles">
      <iframe
        allowtransparency="true"
        border="0"
        frameborder="0"
        referrerpolicy="strict-origin-when-cross-origin"
        scrolling="no"
        :src="state.src" />
    </div>
  </div>
</template>
<script lang="ts">
  export default {
    name: 'Login',
  };
</script>

<script setup lang="ts">
  type LoginInfo = {
    src: string,
    width: number,
    height: number,
  }

  const state = reactive({
    src: '',
    width: 800,
    height: 510,
    isShow: false,
  });

  const styles = computed(() => ({ width: `${state.width}px`, height: `${state.height}px` }));

  const showLogin = ({ src, width, height }: LoginInfo) => {
    state.src = src;
    state.width = width;
    state.height = height;
    state.isShow = true;
  };

  const hideLogin = () => {
    state.isShow = false;
  };

  watch(() => state.isShow, () => {
    window.login.isShow = state.isShow;
  });

  window.login = {
    isShow: state.isShow,
    showLogin,
    hideLogin,
  };
</script>

<style lang="less" scoped>
  .login-modal {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 99999;
    font-size: 0;
    background-color: rgb(0 0 0 / 60%);

    &__container {
      position: relative;
      display: block;
      width: 400px;
      height: 400px;
      margin: calc((100vh - 470px) / 2) auto;
      overflow: hidden;
      background-color: #fff;
      border-radius: 2px;
    }

    iframe {
      width: 100%;
      height: 100%;
    }
  }
</style>
