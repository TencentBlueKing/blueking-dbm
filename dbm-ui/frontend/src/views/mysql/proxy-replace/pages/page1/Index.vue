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
  <div class="proxy-replace-page">
    <BkAlert
      closable
      theme="info"
      :title="t('对集群的Proxy实例进行替换')" />
    <div class="proxy-replace-types">
      <strong class="proxy-replace-types-title">
        {{ t('替换类型') }}
      </strong>
      <div class="mt-8 mb-8">
        <CardCheckbox
          v-model="replaceType"
          :desc="t('只替换目标实例')"
          icon="rebuild"
          :title="t('实例替换')"
          :true-value="ProxyReplaceTypes.MYSQL_PROXY_REPLACE" />
        <CardCheckbox
          v-model="replaceType"
          class="ml-8"
          :desc="t('主机关联的所有实例一并替换')"
          icon="host"
          :title="t('整机替换')"
          :true-value="ProxyReplaceTypes.MYSQL_PROXY_HOST_REPLACE" />
      </div>
    </div>
    <Component :is="renderComponent" />
  </div>
</template>

<script setup lang="tsx">
  import { type Component, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import ReplaceHost from './components/ReplaceHost/Index.vue';
  import ReplaceInstance from './components/ReplaceInstance/Index.vue';

  enum ProxyReplaceTypes {
    MYSQL_PROXY_REPLACE = 'MYSQL_PROXY_REPLACE',
    MYSQL_PROXY_HOST_REPLACE = 'MYSQL_PROXY_HOST_REPLACE',
  }

  const ProxyReplaceMap: Record<ProxyReplaceTypes, Component> = {
    [ProxyReplaceTypes.MYSQL_PROXY_REPLACE]: ReplaceInstance,
    [ProxyReplaceTypes.MYSQL_PROXY_HOST_REPLACE]: ReplaceHost,
  };

  const { t } = useI18n();

  const replaceType = ref<ProxyReplaceTypes>(ProxyReplaceTypes.MYSQL_PROXY_REPLACE);

  const renderComponent = computed(() => ProxyReplaceMap[replaceType.value]);
</script>

<style lang="less">
  .proxy-replace-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
    }

    .proxy-replace-types {
      margin-top: 24px;

      .proxy-replace-types-title {
        position: relative;
        font-size: @font-size-mini;
        color: @title-color;

        &::after {
          position: absolute;
          top: 2px;
          right: -8px;
          color: @danger-color;
          content: '*';
        }
      }
    }

    .safe-action {
      margin: 20px 0;

      .safe-action-text {
        padding-bottom: 2px;
        border-bottom: 1px dashed #979ba5;
      }
    }
  }
</style>
