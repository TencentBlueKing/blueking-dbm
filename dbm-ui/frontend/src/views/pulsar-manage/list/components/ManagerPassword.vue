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
  <BkLoading
    class="pulsar-manager-password-box"
    :loading="isLoading">
    <div class="item">
      <span class="item-label">{{ $t('集群名称') }}：</span>
      <span class="item-value">{{ result.cluster_name || '--' }}</span>
    </div>
    <div class="item">
      <span class="item-label">{{ $t('域名') }}：</span>
      <span class="item-value">{{ result.domain || '--' }}</span>
    </div>
    <div class="item">
      <span class="item-label">{{ $t('Manager 账号') }}：</span>
      <span class="item-value">{{ result.username || '--' }}</span>
      <span
        v-bk-tooltips="$t('复制账号')"
        class="copy-btn">
        <i
          class="db-icon-copy"
          @click="handleCopyUsername" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ $t('Manager 密码') }}：</span>
      <span class="item-value">{{ passwordText }}</span>
      <span
        class="password-btn"
        @click="handlePasswordToggle">
        <Unvisible v-if="isShowPassword" />
        <Eye v-else />
      </span>
      <span
        v-bk-tooltips="$t('复制密码')"
        class="copy-btn">
        <i
          class="db-icon-copy"
          @click="handleCopyPassword" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">Token：</span>
      <span class="item-value">{{ tokenText }}</span>
      <span
        class="password-btn"
        @click="handleTokenToggle">
        <Unvisible v-if="isShowToken" />
        <Eye v-else />
      </span>
      <span
        v-bk-tooltips="$t('复制 Token')"
        class="copy-btn">
        <i
          class="db-icon-copy"
          @click="handleCopyToken" />
      </span>
    </div>
  </BkLoading>
</template>

<script setup lang="ts">
  import {
    Eye,
    Unvisible,
  } from 'bkui-vue/lib/icon';
  import { ref } from 'vue';

  import { getPassword } from '@services/pulsar';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const copy = useCopy();

  const { currentBizId } = useGlobalBizs();

  const isLoading = ref(true);
  const isShowPassword = ref(false);
  const isShowToken = ref(false);
  const result = ref({
    cluster_name: '',
    domain: '',
    username: '',
    password: '',
    token: '',
  });

  getPassword({
    bk_biz_id: currentBizId,
    cluster_id: props.clusterId,
  })
    .then((data) => {
      result.value = data;
    })
    .finally(() => {
      isLoading.value = false;
    });

  const passwordText = computed(() => {
    if (!isShowPassword.value) {
      return '******';
    }
    return result.value.password || '--';
  });
  const tokenText = computed(() => {
    if (!isShowToken.value) {
      return '******';
    }
    return result.value.token || '--';
  });

  const handleCopyUsername = () => {
    copy(result.value.username);
  };

  const handleCopyPassword = () => {
    copy(result.value.password);
  };

  const handleCopyToken = () => {
    copy(result.value.token);
  };

  const handlePasswordToggle = () => {
    isShowPassword.value = !isShowPassword.value;
  };

  const handleTokenToggle = () => {
    isShowToken.value = !isShowToken.value;
  };
</script>

<style lang="less" scoped>
  .pulsar-manager-password-box {
    padding-bottom: 24px;

    .item {
      display: flex;
      padding: 8px 0;
      font-size: 12px;

      .item-label {
        flex-shrink: 0;
        width: 120px;
        text-align: right;
      }

      .item-value {
        color: @title-color;
        word-break: break-all;
      }

      .copy-btn,
      .password-btn {
        display: inline-block;
        margin-left: 4px;
        font-size: @font-size-normal;
        color: @primary-color;
        cursor: pointer;

        .db-icon-copy {
          vertical-align: text-top;
        }
      }
    }
  }
</style>
