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
        <span class="title-success">{{ submitRes?.success?.length || 0 }}</span>
        <span class="title-error">{{ errorListLength }}</span>
      </I18nT>
    </template>
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
          <span>
            {{ t('失败的实例') }}({{ errorListLength }})
          </span>
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

  import { modifyMysqlAdminPassword } from '@services/permission';

  import { useCopy } from '@hooks';

  import RenderSuccess from '@views/mysql/common/ticket-success/Index.vue';

  type ModifyMysqlAdminPassword = ServiceReturnType<typeof modifyMysqlAdminPassword>

  interface Props {
    submitRes?: ModifyMysqlAdminPassword
  }

  interface Emits {
    (e: 'retry', value: ModifyMysqlAdminPassword['fail']): void
    (e: 'refresh'): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();

  const errorList = computed(() => props?.submitRes?.fail || []);
  const errorListLength = computed(() => errorList.value.length);

  const handleCopy = () => {
    copy(errorList.value.join(','));
  };

  const handleRetry = () => {
    // TODO
    // emits('retry', errorList.value);
  };

  const handleGoBack = () => {
    emits('refresh');
  };
</script>

<style lang="less" scoped>
.password-temporary-modify-success {
  padding: 60px 0;
  background-color: #FFF;

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
    background-color: #F5F7FA;

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
