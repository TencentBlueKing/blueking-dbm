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
    class="cluster-password"
    :is-show="isShow"
    :title="title ||$t('获取访问方式')"
    @closed="handleClose">
    <BkLoading :loading="state.isLoading">
      <div class="cluster-password__content">
        <div class="cluster-password__item">
          <span class="cluster-password__item-label">{{ $t('集群名称') }}：</span>
          <span class="cluster-password__item-value">{{ state.data.cluster_name || '--' }}</span>
        </div>
        <div class="cluster-password__item">
          <span class="cluster-password__item-label">{{ $t('域名') }}：</span>
          <span class="cluster-password__item-value">
            <span>{{ state.data.domain || '--' }}</span>
            <span
              v-bk-tooltips="$t('复制')"
              class="password-btn">
              <i
                class="db-icon-copy"
                @click="copy(state.data.domain)" />
            </span>
          </span>
        </div>
        <div class="cluster-password__item">
          <span class="cluster-password__item-label">{{ $t('Proxy密码') }}：</span>
          <span class="cluster-password__item-value">
            <span>{{ passwordText }}</span>
            <span
              class="password-btn"
              @click="handlePasswordToggle">
              <Unvisible v-if="isShowPassword" />
              <Eye v-else />
            </span>
            <!-- <i
              class="db-icon-copy"
              @click="handleCopy" /> -->
          </span>
        </div>
      </div>
    </BkLoading>
    <template #footer>
      <BkButton @click="handleClose">
        {{ $t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import {
    Eye,
    Unvisible,
  } from 'bkui-vue/lib/icon';
  import type { PropType } from 'vue';

  import { getClusterPassword } from '@services/clusters';
  import type { ClusterPasswordParams } from '@services/types/clusters';

  import { useCopy } from '@hooks';

  const props = defineProps({
    isShow: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
    fetchParams: {
      type: Object as PropType<ClusterPasswordParams>,
      required: true,
    },
  });

  const emits = defineEmits(['update:is-show']);
  const copy = useCopy();
  const state = reactive({
    isLoading: false,
    data: initData(),
  });
  const isShowPassword = ref(false);
  const passwordText = computed(() => (isShowPassword.value ? state.data.password : '*********'));

  // 获取集群密码
  watch(() => props.isShow, (isShow) => {
    if (isShow) {
      state.isLoading = true;
      getClusterPassword(props.fetchParams)
        .then((res) => {
          state.data = res;
        })
        .catch(() => {
          state.data = initData();
        })
        .finally(() => {
          state.isLoading = false;
        });
    }
  });

  function handlePasswordToggle() {
    isShowPassword.value = !isShowPassword.value;
  }

  function initData() {
    return {
      cluster_name: '',
      domain: '',
      password: '',
    };
  }

  function handleClose() {
    emits('update:is-show', false);
    setTimeout(() => {
      state.data = initData();
      isShowPassword.value = false;
    }, 500);
  }
</script>

<style lang="less" scoped>
  .cluster-password {
    .bk-form-item {
      margin-bottom: 0;
    }

    :deep(.bk-form-label) {
      padding-right: 8px;
    }

    &__content {
      padding-bottom: 48px;
      font-size: @font-size-mini;
    }

    &__item {
      display: flex;
      padding-bottom: 16px;

      &-label {
        flex-shrink: 0;
        width: 100px;
        text-align: right;
      }

      &-value {
        color: @title-color;
        word-break: break-all;

        .db-icon-copy,
        .password-btn {
          display: inline-block;
          margin-left: 4px;
          font-size: @font-size-normal;
          color: @primary-color;
          vertical-align: middle;
          cursor: pointer;
        }
      }
    }
  }
</style>
