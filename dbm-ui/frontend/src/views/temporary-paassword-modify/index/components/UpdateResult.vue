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
  <RenderSuccess
    class="password-temporary-modify-success"
    :steps="[]">
    <template #title>
      <I18nT
        keypath="密码修改完成，成功n个，失败n个"
        tag="span">
        <span class="title-success">{{ successListLength }}</span>
        <span class="title-error">{{ errorListLength }}</span>
      </I18nT>
    </template>
    <slot />
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
          :disabled="!errorListLength"
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
        v-if="errorListLength"
        class="list-box">
        <div class="list-box-head">
          <span> {{ t('失败的实例') }}({{ errorListLength }}) </span>
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
            {{ item.ip }}:{{ item.port }}
          </span>
        </div>
      </div>
    </template>
  </RenderSuccess>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { modifyAdminPassword } from '@services/source/permission';

  import { useCopy } from '@hooks';

  import type { ClusterTypes } from '@common/const';

  import RenderSuccess from '@components/ticket-success/Index.vue';

  type ModifyAdminPassword = ServiceReturnType<typeof modifyAdminPassword>;

  interface RetryItem {
    ip: string;
    port: number;
    bk_cloud_id: number;
    cluster_type: ClusterTypes;
    role: string;
  }

  interface Props {
    submitRes?: ModifyAdminPassword;
    submitLength: number;
    submitRoleMap: Record<string, string>;
    password: string;
  }

  interface Emits {
    (e: 'retry', value: RetryItem[]): void;
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();
  const isShowPassword = ref(false);

  const passwordDisplay = computed(() => (isShowPassword.value ? props.password : '********'));
  const errorList = computed(() =>
    (props?.submitRes?.fail || []).reduce((errorPrev, errorItem) => {
      const { bk_cloud_id, cluster_type } = errorItem;
      const roleMap = props.submitRoleMap;
      const retryItems = errorItem.instances.reduce((retryItemsPrev, instanceItem) => {
        const newInstanceItem = instanceItem.addresses.map((addressItem) => ({
          ...addressItem,
          bk_cloud_id,
          cluster_type,
          role: roleMap[`${addressItem.ip}:${addressItem.port}`],
        }));

        return [...retryItemsPrev, ...newInstanceItem];
      }, [] as RetryItem[]);

      return [...errorPrev, ...retryItems];
    }, [] as RetryItem[]),
  );
  const errorListLength = computed(() => errorList.value.length);
  const successListLength = computed(() => props.submitLength - errorListLength.value);

  const handleShowPassword = () => {
    isShowPassword.value = !isShowPassword.value;
  };

  const handleCopyPassword = () => {
    copy(props.password);
  };

  const handleCopy = () => {
    const copyList = errorList.value.map((errorItem) => `${errorItem.ip}:${errorItem.port}`);
    copy(copyList.join('\n'));
  };

  const handleRetry = () => {
    emits('retry', errorList.value);
  };

  const handleGoBack = () => {
    emits('refresh');
  };
</script>

<style lang="less" scoped>
  .password-temporary-modify-success {
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
