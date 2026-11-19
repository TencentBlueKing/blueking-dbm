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
  <DbSideslider
    ref="sideslider"
    v-model:is-show="isShow"
    class="dns-domain-create"
    :title="t('新建域名')"
    :width="980">
    <DbForm
      ref="form"
      class="dns-domain-create-form"
      form-type="vertical"
      :model="formData"
      :rules="rules">
      <!-- 格式提示放在输入框下方，校验报错时由错误信息替换 -->
      <FormItemWithHint
        :label="t('域名')"
        :model="formData.prefix"
        property="prefix"
        required
        :rules="rules.prefix">
        <DomainInput v-model="formData.prefix" />
        <template #hint>
          {{ t('至少 3 段，如 api.game.db；仅支持小写字母、数字、连字符和点号；') }}
          <span class="dns-domain-create-hint-warning">{{ t('创建后不可改') }}</span>
        </template>
      </FormItemWithHint>
      <BkFormItem
        :description="t('一个域名可对应多个 IP，重复地址自动去重')"
        label="IP"
        property="ips"
        required>
        <DbTagInput
          v-model="formData.ips"
          allow-create
          multiple
          :placeholder="t('请输入 IP，按 Enter 确认')" />
      </BkFormItem>
      <BkFormItem
        :label="t('负责人')"
        property="owners"
        required>
        <DbMemberSelector v-model="formData.owners" />
      </BkFormItem>
      <BkFormItem
        :label="t('备注')"
        property="remark">
        <BkInput
          v-model="formData.remark"
          :maxlength="500"
          :rows="4"
          type="textarea" />
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="w-88 mr-8"
        :disabled="!isRequiredFilled"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('创建') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleCancelClick">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkDnsDomainDuplicate, createDnsDomain } from '@services/source/dnsDomain';

  import { useUserProfile } from '@stores';

  import DbMemberSelector from '@components/db-member-selector/index.vue';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import {
    DOMAIN_SUFFIX,
    hasMinDomainLabels,
    isValidDomain,
    isValidDomainChars,
    isValidIpList,
  } from '@views/dns-domain/utils';

  import { messageSuccess } from '@utils';

  import DomainInput from './components/DomainInput.vue';

  type Emits = (e: 'success', domain: string) => void;

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();
  const userProfile = useUserProfile();

  const sidesliderRef = useTemplateRef('sideslider');
  const formRef = useTemplateRef('form');

  const createDefaultData = () => ({
    ips: [] as string[],
    // 负责人默认当前用户，可修改
    owners: userProfile.username ? [userProfile.username] : [],
    prefix: '',
    remark: '',
  });

  const formData = reactive(createDefaultData());
  const isSubmitting = ref(false);

  const rules = {
    ips: [
      {
        message: t('请输入不带端口的 IPv4 地址'),
        trigger: 'change',
        validator: (value: string[]) => isValidIpList(value),
      },
    ],
    owners: [
      {
        message: t('至少保留 1 人'),
        trigger: 'change',
        validator: (value: string[]) => value.length > 0,
      },
    ],
    // 依次校验，提示第一条不满足的规则；校验对象为拼上 .db 后的完整域名
    prefix: [
      {
        message: t('仅支持小写字母、数字、连字符和点号'),
        trigger: 'blur',
        validator: (value: string) => isValidDomainChars(`${value.trim()}${DOMAIN_SUFFIX}`),
      },
      {
        message: t('域名至少 3 段，如 api.game.db'),
        trigger: 'blur',
        validator: (value: string) => hasMinDomainLabels(`${value.trim()}${DOMAIN_SUFFIX}`),
      },
      {
        message: t('每段首尾须为字母或数字，单段不超过 63 字符，总长不超过 253 字符'),
        trigger: 'blur',
        validator: (value: string) => isValidDomain(`${value.trim()}${DOMAIN_SUFFIX}`),
      },
      // 格式规则全部通过才会执行到这里（表单项按顺序校验、遇失败即停），避免触发后端参数校验错误；
      // 接口失败不弹提示、视为通过，由创建接口的「域名已存在」兜底
      {
        message: t('域名已存在'),
        trigger: 'blur',
        validator: (value: string) =>
          checkDnsDomainDuplicate({
            domain: `${value.trim()}${DOMAIN_SUFFIX}`,
          }).then((data) => !data.duplicated),
      },
    ],
  };

  // 主按钮按必填内容启用
  const isRequiredFilled = computed(
    () => formData.prefix.trim() !== '' && formData.ips.length > 0 && formData.owners.length > 0,
  );

  // 每次打开都从默认值开始
  watch(isShow, () => {
    if (isShow.value) {
      Object.assign(formData, createDefaultData());
    }
  });

  // 点取消按钮：内容编辑过先弹离开确认，确认离开后再关闭
  const handleCancelClick = async () => {
    if (await sidesliderRef.value!.beforeClose()) {
      isShow.value = false;
    }
  };

  const handleSubmit = () => {
    formRef.value!.validate().then(() => {
      isSubmitting.value = true;
      createDnsDomain({
        domain: `${formData.prefix.trim()}${DOMAIN_SUFFIX}`,
        ips: [...new Set(formData.ips)],
        owners: formData.owners,
        remark: formData.remark,
      })
        .then((data) => {
          messageSuccess(t('创建成功'));
          isShow.value = false;
          emits('success', data.domain);
        })
        .finally(() => {
          isSubmitting.value = false;
        });
    });
  };
</script>
<style lang="less">
  .dns-domain-create {
    .dns-domain-create-form {
      padding: 20px 24px;
    }

    .dns-domain-create-hint-warning {
      color: #ff9c01;
    }
  }
</style>
