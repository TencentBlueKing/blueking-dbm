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
  <DbDialog
    ref="dialog"
    v-model:is-show="isShow"
    :title="t('删除域名')"
    :width="480">
    <div class="dns-domain-delete">
      <I18nT
        keypath="删除后不可恢复。请输入完整域名 n 确认。"
        scope="global"
        tag="p">
        <strong>{{ domain }}</strong>
      </I18nT>
      <BkInput
        v-model="confirmDomain"
        class="mt-8" />
    </div>
    <template #footer>
      <BkButton
        class="w-88 mr-8"
        :disabled="confirmDomain !== domain"
        :loading="isSubmitting"
        theme="danger"
        @click="handleSubmit">
        {{ t('删除') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleCancelClick">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { deleteDnsDomain } from '@services/source/dnsDomain';

  import { messageSuccess } from '@utils';

  interface Props {
    domain: string;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const dialogRef = useTemplateRef('dialog');

  const confirmDomain = ref('');
  const isSubmitting = ref(false);

  watch(isShow, () => {
    if (isShow.value) {
      confirmDomain.value = '';
    }
  });

  // 点取消按钮：与关闭图标走同一条关闭检查
  const handleCancelClick = async () => {
    if (await dialogRef.value!.beforeClose()) {
      isShow.value = false;
    }
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    deleteDnsDomain({
      confirm_domain: confirmDomain.value,
      domain: props.domain,
    })
      .then(() => {
        messageSuccess(t('删除成功'));
        isShow.value = false;
        emits('success');
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
<style lang="less">
  .dns-domain-delete {
    font-size: 12px;
    color: #63656e;

    strong {
      color: #313238;
      word-break: break-all;
    }
  }
</style>
