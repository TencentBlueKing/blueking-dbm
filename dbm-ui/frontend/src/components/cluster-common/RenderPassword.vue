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
    class="cluster-username-password-box"
    :loading="isLoading">
    <div class="item">
      <span class="item-label">{{ t('集群名称') }}：</span>
      <span class="item-value">{{ result.cluster_name || '--' }}</span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('域名') }}：</span>
      <span class="item-value">{{ `${result.domain}:${result.access_port}` }}</span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('账号') }}：</span>
      <span class="item-value">{{ result.username || '--' }}</span>
      <span
        v-bk-tooltips="t('复制账号')"
        class="copy-btn">
        <i
          class="db-icon-copy"
          @click="() => handleCopy('username')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('密码') }}：</span>
      <span class="item-value">{{ passwordText }}</span>
      <span
        class="password-btn"
        @click="handlePasswordToggle">
        <Unvisible v-if="isShowPassword" />
        <Eye v-else />
      </span>
      <span
        v-bk-tooltips="t('复制密码')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('password')" />
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
  import { useI18n } from 'vue-i18n';

  import { getPulsarPassword } from '@services/source/pulsar';

  import { useCopy } from '@hooks';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const copy = useCopy();
  const { t } = useI18n();

  const isLoading = ref(true);
  const isShowPassword = ref(false);
  const result = ref({
    access_port: 0,
    cluster_name: '',
    domain: '',
    username: '',
    password: '',
    token: '',
  });

  getPulsarPassword({ cluster_id: props.clusterId })
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


  const handleCopy = (type: 'username' | 'password') => {
    const {
      username,
      password,
      token,
    } = result.value;
    if (type === 'username') {
      copy(username);
      return;
    }
    if (token) {
      copy(`${password} ${token}`);
      return;
    }
    copy(password);
  };

  const handlePasswordToggle = () => {
    isShowPassword.value = !isShowPassword.value;
  };

</script>

<style lang="less" scoped>
  .cluster-username-password-box {
    padding-bottom: 24px;

    .item {
      display: flex;
      padding: 8px 0;
      font-size: 12px;
      align-items: center;

      .item-label {
        flex-shrink: 0;
        width: 100px;
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
      }

    }
  }
</style>
