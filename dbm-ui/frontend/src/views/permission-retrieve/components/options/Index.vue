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
  <div class="permission-retrieve-options">
    <BkForm
      ref="formRef"
      form-type="vertical"
      :model="formData">
      <IpItem v-model="formData.ips" />
      <DomainItem
        ref="domainItemRef"
        v-model="formData.immute_domains"
        v-model:cluster-type="formData.cluster_type"
        v-model:is-master="formData.is_master"
        :account-type="accountType" />
      <BkFormItem
        :label="t('账号')"
        property="users"
        required>
        <UserSelect
          v-model="formData.users"
          :form-data="formData" />
      </BkFormItem>
      <BkFormItem
        :label="t('访问 DB')"
        property="dbs">
        <BkTagInput
          v-model="formData.dbs"
          allow-auto-match
          allow-create
          collapse-tags
          has-delete-icon
          :placeholder="t('请输入DB，支持%')" />
      </BkFormItem>
    </BkForm>
    <div class="mb-24">
      <BkButton
        class="w-88"
        :loading="loading"
        theme="primary"
        @click="handleSearch">
        {{ t('查询') }}
      </BkButton>
      <BkButton
        class="ml8 w-88"
        :disabled="loading"
        @click="handleReset">
        {{ t('重置') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { Form } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { AccountTypes, ClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import DomainItem from './components/item/Domain.vue';
  import IpItem from './components/item/Ip.vue';
  import UserSelect from './components/item/UserSelect.vue';

  interface Props {
    loading: boolean;
    accountType: AccountTypes;
  }

  interface Emits {
    (
      e: 'change',
      params?: {
        ips: string;
        immute_domains: string;
        users: string;
        dbs: string;
        cluster_type: ClusterTypes;
        account_type: AccountTypes;
        is_master: boolean;
      },
    ): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const getDefaultFormData = () => ({
    ips: '',
    immute_domains: '',
    users: [] as string[],
    dbs: [] as string[],
    cluster_type: ClusterTypes.TENDBSINGLE,
    account_type: props.accountType,
    is_master: true,
  });

  const formRef = ref<InstanceType<typeof Form>>();
  const domainItemRef = ref<InstanceType<typeof DomainItem>>();

  const formData = reactive(getDefaultFormData());

  const handleSearch = () => {
    formRef.value!.validate().then(() => {
      const params = {
        ...formData,
        ips: formData.ips.replace(batchSplitRegex, ','),
        immute_domains: formData.immute_domains.replace(batchSplitRegex, ','),
        users: formData.users.join(','),
        dbs: formData.dbs.join(','),
      };
      emits('change', params);
    });
  };

  const handleReset = () => {
    domainItemRef.value!.reset();
    Object.assign(formData, getDefaultFormData());
    emits('change');
    nextTick(() => {
      formRef.value!.clearValidate();
    });
  };
</script>

<style lang="less">
  .permission-retrieve-options {
    .bk-form {
      display: flex;

      .bk-form-item {
        flex: 1;

        &:not(:last-child) {
          margin-right: 24px;
        }
      }
    }

    .input-suffix {
      display: flex;
      width: 32px;
      border-left: 1px solid #c4c6cc;
      align-items: center;
      justify-content: center;
    }
  }
</style>
