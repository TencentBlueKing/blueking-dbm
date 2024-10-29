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
        v-model="formData.immute_domains" />
      <UserItem
        ref="userRefItem"
        v-model="formData.users" />
      <DbItem v-model="formData.dbs" />
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
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { AccountTypes, ClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import DbItem from './components/item/Db.vue';
  import DomainItem from './components/item/Domain.vue';
  import IpItem from './components/item/Ip.vue';
  import UserItem from './components/item/user/Index.vue';

  interface Props {
    loading: boolean;
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

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();

  const getDefaultFormData = () => ({
    ips: '',
    immute_domains: '',
    users: [] as string[],
    dbs: [] as string[],
  });

  const { accountType } = route.meta as { accountType: AccountTypes };

  const formRef = ref<ComponentExposed<typeof Form>>();
  const domainItemRef = ref<InstanceType<typeof DomainItem>>();
  const userRefItem = ref<InstanceType<typeof UserItem>>();

  const formData = reactive(getDefaultFormData());

  watch(
    () => [formData.ips, formData.immute_domains],
    () => {
      formRef.value!.validate(['ips', 'immute_domains']).then(() => {
        userRefItem.value!.getUserList({
          ips: formData.ips.replace(batchSplitRegex, ','),
          immute_domains: formData.immute_domains.replace(batchSplitRegex, ','),
          cluster_type: domainItemRef.value!.getClusterType(),
          account_type: accountType as AccountTypes,
          limit: -1,
          offset: 0,
        });
      });
    },
  );

  const handleSearch = () => {
    formRef.value!.validate().then(() => {
      const params = {
        ips: formData.ips.replace(batchSplitRegex, ','),
        immute_domains: formData.immute_domains.replace(batchSplitRegex, ','),
        users: formData.users.join(','),
        dbs: formData.dbs.join(','),
        cluster_type: domainItemRef.value!.getClusterType(),
        account_type: accountType as AccountTypes,
        is_master: domainItemRef.value!.isMaster(),
      };
      emits('change', params);
    });
  };

  const handleReset = () => {
    domainItemRef.value!.reset();
    Object.assign(formData, getDefaultFormData());
    emits('change');
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
