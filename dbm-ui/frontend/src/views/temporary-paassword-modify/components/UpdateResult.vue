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
    v-if="isActive"
    class="submitting-mask">
    <DbIcon
      class="submitting-icon"
      svg
      type="sync-pending" />
    <p class="submitting-text mt16">
      {{ t('密码正在修改中，请稍等') }}
    </p>
    <RouterLink
      class="mt16 mb16"
      target="_blank"
      :to="{
        name: 'taskHistoryDetail',
        params: {
          root_id: rootId,
        },
      }">
      {{ t('查看详情') }}
    </RouterLink>
  </div>
  <RenderSuccess
    v-else
    class="modify-success"
    :steps="[]">
    <template #title>
      <I18nT
        keypath="密码修改完成，成功n个，失败n个"
        tag="span">
        <span class="title-success">{{ successList.length }}</span>
        <span class="title-error">{{ errorList.length }}</span>
      </I18nT>
    </template>
    <RouterLink
      class="mt16 mb16"
      target="_blank"
      :to="{
        name: 'taskHistoryDetail',
        params: {
          root_id: rootId,
        },
      }">
      {{ t('查看详情') }}
    </RouterLink>
    <div class="password-display">
      {{ t('当前密码') }} : {{ passwordDisplay }}
      <BkButton
        class="ml-8"
        text
        theme="primary"
        @click="handleShowPassword">
        <DbIcon
          v-if="!isShowPassword"
          type="bk-dbm-icon db-icon-visible1" />
        <DbIcon
          v-else
          type="bk-dbm-icon db-icon-invisible1" />
      </BkButton>
      <BkButton
        class="ml-4"
        text
        theme="primary"
        @click="handleCopyPassword">
        <DbIcon type="copy" />
      </BkButton>
    </div>
    <template #action>
      <div>
        <BkButton
          :disabled="!errorList.length"
          theme="primary"
          @click="handleRetry">
          {{ t('失败重试') }}
        </BkButton>
        <BkButton
          class="ml8"
          @click="handleGoBack">
          {{ t('返回') }}
        </BkButton>
      </div>
      <div
        v-if="errorList.length || errorMessage"
        class="list-box">
        <template v-if="errorMessage">
          <div class="list-box-head">
            {{ t('错误日志') }}
          </div>
          <div class="list-box-content mb-12">
            {{ errorMessage }}
          </div>
        </template>
        <template v-if="errorList.length">
          <div class="list-box-head">
            {{ t('失败的实例') }}({{ errorList.length }})
            <BkButton
              text
              theme="primary"
              @click="handleCopy">
              <DbIcon type="copy" />
            </BkButton>
          </div>
          <div class="list-box-content">
            <span
              v-for="(item, index) in errorList"
              :key="index"
              class="list-box-content-item">
              {{ item }}
            </span>
          </div>
        </template>
      </div>
    </template>
  </RenderSuccess>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { modifyAdminPassword, queryAsyncModifyResult } from '@services/source/permission';

  import RenderSuccess from '@components/ticket-success/Index.vue';

  import { execCopy } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  interface Props {
    instanceList: ServiceParameters<typeof modifyAdminPassword>['instance_list'];
    password: string;
    rootId: string;
  }

  interface Emits {
    (e: 'retry', value: Props['instanceList']): void;
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowPassword = ref(false);
  const successList = ref<string[]>([]);
  const errorList = ref<string[]>([]);
  const errorMessage = ref('');

  const passwordDisplay = computed(() => (isShowPassword.value ? props.password : '********'));

  const getInstanceList = (list: ServiceReturnType<typeof queryAsyncModifyResult>['success'] = []) => {
    const arr: string[] = [];
    list.forEach((item) => {
      item.instances.forEach((insItem) => {
        insItem.addresses.forEach((addressItem) => {
          arr.push(`${addressItem.ip}:${addressItem.port}`);
        });
      });
    });
    return arr;
  };

  const { run: queryAsyncModifyResultRun } = useRequest(queryAsyncModifyResult, {
    manual: true,
    onSuccess(data) {
      /**
       * 设置轮询
       * FINISHED: 完成态
       * FAILED: 失败态
       * REVOKED: 取消态
       */
      if (['FINISHED', 'FAILED', 'REVOKED'].includes(data.status)) {
        pause();
      } else if (!isActive.value) {
        resume();
      }
      if (data.status === 'FINISHED') {
        errorMessage.value = data.error as string;
        successList.value = data.success ? getInstanceList(data.success) : [];
        errorList.value = data.fail
          ? getInstanceList(data.fail)
          : props.instanceList
              .map((item) => `${item.ip}:${item.port}`)
              .filter((item) => !successList.value.includes(item));
      }
    },
  });

  // 轮询
  const { isActive, resume, pause } = useTimeoutPoll(() => {
    queryAsyncModifyResultRun({
      root_id: props.rootId,
    });
  }, 2000);

  watch(
    () => props.rootId,
    () => {
      if (props.rootId && !isActive.value) {
        resume();
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowPassword = () => {
    isShowPassword.value = !isShowPassword.value;
  };

  const handleCopyPassword = () => {
    execCopy(props.password, t('复制成功，共n条', { n: 1 }));
  };

  const handleCopy = () => {
    execCopy(errorList.value.join('\n'), t('复制成功，共n条', { n: errorList.value.join('\n') }));
  };

  const handleRetry = () => {
    emits(
      'retry',
      props.instanceList.filter((item) => !successList.value.includes(`${item.ip}:${item.port}`)),
    );
  };

  const handleGoBack = () => {
    emits('refresh');
  };

  onBeforeUnmount(() => {
    pause();
  });
</script>

<style lang="less" scoped>
  .submitting-mask {
    display: flex;
    padding: 90px 0 138px;
    flex-direction: column;
    align-items: center;

    .submitting-icon {
      font-size: 64px;
      color: @primary-color;
      animation: rotate 2s linear infinite;
    }

    .submitting-text {
      font-size: 24px;
      color: #313238;
    }

    @keyframes rotate {
      0% {
        transform: rotate(0deg);
      }

      100% {
        transform: rotate(-360deg);
      }
    }
  }

  .modify-success {
    padding: 60px 0;
    background-color: #fff;

    .password-display {
      height: 40px;
      line-height: 40px;
    }

    :deep(.operation-steps) {
      display: none;
    }

    :deep(.action) {
      margin-top: 16px;
    }

    .title-success {
      font-weight: bold;
      color: @success-color;
    }

    .title-error {
      font-weight: bold;
      color: @danger-color;
    }

    .list-box {
      max-width: 820px;
      padding: 16px;
      margin: 24px auto 0;
      text-align: left;
      background-color: #f5f7fa;

      .list-box-head {
        margin-bottom: 12px;
        font-weight: bold;
        color: #313238;
      }

      .list-box-content {
        display: flex;
        flex-wrap: wrap;

        .list-box-content-item {
          width: 20%;
          line-height: 24px;
        }
      }
    }
  }
</style>
