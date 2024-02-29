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
    <div class="copy-info">
      <BkButton
        text
        theme="primary"
        @click="() => handleCopy('all')">
        {{ t('复制信息') }}
      </BkButton>
    </div>
    <div class="item">
      <span class="item-label">{{ t('集群名称') }}：</span>
      <span class="item-value">{{ result.cluster_name || '--' }}</span>
      <span
        v-bk-tooltips="t('复制集群名称')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('cluster_name')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('域名') }}：</span>
      <span class="item-value">{{ result.domain || '--' }}</span>
      <span
        v-bk-tooltips="t('复制域名')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('domain')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('Manager 账号') }}：</span>
      <span class="item-value">{{ result.username || '--' }}</span>
      <span
        v-bk-tooltips="t('复制账号')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('username')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('Manager 密码') }}：</span>
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
        v-bk-tooltips="t('复制 Token')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('token')" />
      </span>
    </div>
  </BkLoading>
</template>

<script setup lang="ts">
  import { Eye, Unvisible } from 'bkui-vue/lib/icon';
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
  const isShowToken = ref(false);
  const result = ref({
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
  const tokenText = computed(() => {
    if (!isShowToken.value) {
      return '******';
    }
    return result.value.token || '--';
  });

  const handleCopy = (type: string) => {
    const { cluster_name, domain, username, password, token } = result.value;
    switch (type) {
      case 'cluster_name':
        copy(cluster_name);
        break;
      case 'domain':
        copy(domain);
        break;
      case 'username':
        copy(username);
        break;
      case 'password':
        copy(password);
        break;
      case 'token':
        copy(token);
        break;
      default:
        // 复制全部
        // eslint-disable-next-line no-case-declarations, camelcase
        const content = `${t('集群名称')}: ${cluster_name}\n${t('域名')}: ${domain}\n${t('Manager 账号')}: ${username}\n${t('Manager 密码')}: ${password}\nToken: ${token}`;
        copy(content);
        break;
    }
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

    .copy-info {
      position: absolute;
      top: 18px;
      left: 160px;
    }

    .item {
      display: flex;
      padding: 8px 0;
      font-size: 12px;

      &:hover {
        .copy-btn {
          visibility: visible;
        }
      }

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
        font-size: @font-size-mini;
        color: @primary-color;
        cursor: pointer;

        .db-icon-copy {
          vertical-align: text-top;
        }
      }

      .copy-btn {
        visibility: hidden;
      }
    }
  }
</style>
