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
      <BkFormItem
        :description="t('仅支持小写字母、数字、连字符和点号；创建后不可修改')"
        :label="t('域名')"
        property="prefix"
        required>
        <DomainInput v-model="formData.prefix" />
      </BkFormItem>
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

  import { createDnsDomain } from '@services/source/dnsDomain';

  import { useUserProfile } from '@stores';

  import DbMemberSelector from '@components/db-member-selector/index.vue';

  import { DOMAIN_SUFFIX, isValidDomain, isValidIpList } from '@views/dns-domain/utils';

  import { messageSuccess } from '@utils';

  import DomainInput from './components/DomainInput.vue';

  type Emits = (e: 'success') => void;

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
    prefix: [
      {
        message: t(
          '域名格式不正确：每段为小写字母、数字、连字符，首尾为字母或数字，单段不超过 63 字符，总长不超过 253 字符',
        ),
        trigger: 'blur',
        validator: (value: string) => isValidDomain(`${value.trim()}${DOMAIN_SUFFIX}`),
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
        .then(() => {
          messageSuccess(t('创建成功'));
          isShow.value = false;
          emits('success');
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
  }
</style>
