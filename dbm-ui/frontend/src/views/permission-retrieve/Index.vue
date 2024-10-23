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
  <BkLoading
    :loading="loading"
    :z-index="100">
    <div class="permission-retrieve">
      <BkCard
        is-collapse
        :title="t('查询条件')">
        <Options
          ref="optionsRef"
          v-model="formData"
          v-model:is-master="isMaster"
          class="ml-8"
          :loading
          @reset="handleReset"
          @search="handleSearch" />
      </BkCard>
      <BkCard
        class="mt-16"
        is-collapse
        :title="t('查询结果')">
        <Result
          ref="resultRef"
          v-model="formData.format_type"
          class="ml-8"
          :data="data"
          :db-memo="dbMemo"
          :is-master="isMaster"
          @export="handleExport"
          @search="handleSearch" />
      </BkCard>
    </div>
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAccountPrivs, getDownloadPrivs } from '@services/source/mysqlPermissionAccount';

  import { batchSplitRegex } from '@common/regex';

  import Options from './components/options/Index.vue';
  import Result from './components/result/Index.vue';

  const { t } = useI18n();

  const getDefaultFormData = () => ({
    ips: '',
    immute_domains: '',
    users: [] as string[],
    dbs: [] as string[],
    format_type: 'ip',
  });

  const optionsRef = ref<InstanceType<typeof Options>>();
  const resultRef = ref<InstanceType<typeof Result>>();
  const isMaster = ref(true);

  const dbMemo = shallowRef<string[]>([]);

  const formData = reactive(getDefaultFormData());

  const {
    run: runGetAccountPrivs,
    data,
    mutate,
    loading,
  } = useRequest(getAccountPrivs, {
    manual: true,
    onError() {
      mutate({
        match_ips_count: 0,
        results: {
          privs_for_ip: null,
          privs_for_cluster: null,
          has_priv: null,
          no_priv: null,
        },
      });
    },
  });

  watch(
    () => [formData.ips, formData.immute_domains],
    () => {
      optionsRef.value!.getUserList();
    },
  );

  const getApiParams = (pagination = false) => {
    dbMemo.value = formData.dbs;
    const params = {
      ips: formData.ips.replace(batchSplitRegex, ','),
      immute_domains: formData.immute_domains.replace(batchSplitRegex, ','),
      users: formData.users.join(','),
      format_type: formData.format_type,
      ...optionsRef.value!.getTypes(),
    };

    if (formData.dbs.length) {
      Object.assign(params, { dbs: formData.dbs.join(',') });
    }

    if (pagination) {
      Object.assign(params, resultRef.value!.getPaginationParams());
    }

    return params;
  };

  const handleSearch = () => {
    optionsRef.value!.validate().then(() => {
      runGetAccountPrivs(getApiParams(true));
    });
  };

  const handleReset = () => {
    Object.assign(formData, getDefaultFormData());
    resultRef.value!.resetPagination();
    dbMemo.value = [];
    mutate({
      match_ips_count: 0,
      results: {
        privs_for_ip: null,
        privs_for_cluster: null,
        has_priv: null,
        no_priv: null,
      },
    });
  };

  const handleExport = () => {
    getDownloadPrivs(getApiParams());
  };
</script>

<style lang="less" scoped>
  .permission-retrieve {
    .bk-card {
      border: none;

      :deep(.bk-card-head) {
        border-bottom: none;

        .title {
          margin-left: 8px;
          color: #313238;
        }
      }
    }
  }
</style>
