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
  <SmartAction class="proxy-replace-page">
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
          :true-value="ProxyReplaceTypes.MYSQL_PROXY_REPLACE"
          @update:model-value="handleReplaceTypeChange" />
        <CardCheckbox
          v-model="replaceType"
          class="ml-8"
          :desc="t('主机关联的所有实例一并替换')"
          icon="host"
          :title="t('整机替换')"
          :true-value="ProxyReplaceTypes.MYSQL_PROXY_HOST_REPLACE"
          @update:model-value="handleReplaceTypeChange" />
      </div>
    </div>
    <Component
      :is="renderComponent"
      ref="tableRef"
      :data="data" />
    <div class="safe-action">
      <BkCheckbox
        v-model="isSafe"
        v-bk-tooltips="t('如忽略_在有连接的情况下Proxy也会执行替换')"
        :false-label="false"
        true-label>
        <span class="safe-action-text">{{ t('忽略业务连接') }}</span>
      </BkCheckbox>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { type Component, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { MySQLProxySwitchDetails } from '@services/model/ticket/details/mysql';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import ReplaceHost from './components/ReplaceHost/Index.vue';
  import ReplaceInstance from './components/ReplaceInstance/Index.vue';

  enum ProxyReplaceTypes {
    MYSQL_PROXY_REPLACE = 'MYSQL_PROXY_REPLACE', // 实例替换
    MYSQL_PROXY_HOST_REPLACE = 'MYSQL_PROXY_HOST_REPLACE', // 整机替换
  }

  const ProxyReplaceMap: Record<ProxyReplaceTypes, Component> = {
    [ProxyReplaceTypes.MYSQL_PROXY_REPLACE]: ReplaceInstance,
    [ProxyReplaceTypes.MYSQL_PROXY_HOST_REPLACE]: ReplaceHost,
  };

  const { t } = useI18n();
  const router = useRouter();

  const tableRef = ref();
  const replaceType = ref<ProxyReplaceTypes>(ProxyReplaceTypes.MYSQL_PROXY_REPLACE);
  const data = shallowRef<MySQLProxySwitchDetails['infos']>([]);
  const isSafe = ref(true);
  const isSubmitting = ref(false);

  const renderComponent = computed(() => ProxyReplaceMap[replaceType.value]);

  useTicketCloneInfo({
    type: TicketTypes.MYSQL_PROXY_SWITCH,
    onSuccess(cloneData) {
      const { force, infos } = cloneData;
      data.value = infos;
      isSafe.value = force;
      window.changeConfirm = true;
    },
  });

  const handleReplaceTypeChange = () => {
    data.value = [];
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    tableRef
      .value!.getValue()
      .then((infos: MySQLProxySwitchDetails['infos']) => {
        createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          ticket_type: TicketTypes.MYSQL_PROXY_SWITCH,
          remark: '',
          details: {
            infos,
            is_safe: isSafe.value,
          },
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLProxyReplace',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        });
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableRef.value.reset();
  };
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
