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
    class="permission-dialog"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    height="auto"
    :quick-close="false"
    title=""
    :width="768">
    <PermissionMain :permission="state.permission" />
    <template #footer>
      <BkButton
        v-if="state.applied"
        theme="primary"
        @click="appied">
        {{ $t('已完成') }}
      </BkButton>
      <BkButton
        v-else
        theme="primary"
        @click="apply">
        {{ $t('去申请') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="cancelApply">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script lang="ts">
  import type { Permission } from '@services/types';

  import PermissionMain from './Main.vue';

  export default {
    name: 'PermissionDialog',
  };
</script>

<script setup lang="ts">
  const state = reactive<{
    isShow: boolean;
    applied: boolean;
    permission: Permission | null;
  }>({
    isShow: false,
    applied: false,
    permission: null,
  });

  function showPermission(permission: Permission) {
    state.isShow = true;
    state.permission = permission;
  }

  function apply() {
    if (state.permission) {
      window.open(state.permission.apply_url, '_blank');
      state.applied = true;
    }
  }

  function appied() {
    window.location.reload();
    cancelApply();
  }

  function cancelApply() {
    state.applied = false;
    state.isShow = false;
    // 配合 dialog 关闭延迟防止提前出线空数据界面
    setTimeout(() => {
      state.permission = null;
    }, 400);
  }

  window.permission = {
    show: showPermission,
    isShow: state.isShow,
  };
</script>

<style lang="less" scoped>
  .permission-dialog {
    :deep(.bk-dialog-header) {
      display: none;
    }
  }
</style>
