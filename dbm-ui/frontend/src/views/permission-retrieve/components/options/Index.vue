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
      :model="formData"
      :rules="rules">
      <BkFormItem
        :label="t('源客户端 IP')"
        property="ips"
        required>
        <BatchInput
          v-model="formData.ips"
          icon-type="batch-host-select"
          :max-count="50"
          @icon-click="() => (hostSelectorShow = true)" />
      </BkFormItem>
      <BkFormItem
        :label="t('域名')"
        property="immute_domains"
        required>
        <BatchInput
          v-model="formData.immute_domains"
          icon-type="host-select"
          :max-count="20"
          @change="handleDomainChange"
          @icon-click="() => (clusterSelectorShow = true)" />
      </BkFormItem>
      <BkFormItem
        :label="t('账号')"
        property="users"
        required>
        <UserSelect
          ref="userSelectRef"
          v-model="formData.users" />
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
    <IpSelector
      v-model:show-dialog="hostSelectorShow"
      :biz-id="bizId"
      button-text=""
      :data="selectedHosts"
      :disable-dialog-submit-method="disableHostSubmitMethod"
      :is-cloud-area-restrictions="false"
      :panel-list="['staticTopo', 'manualInput', 'dbmWhitelist']"
      service-mode="all"
      :show-view="false"
      @change="handleChangeIP"
      @change-whitelist="handleChangeWhitelist">
      <template #submitTips="{ hostList: resultHostList }">
        <I18nT
          keypath="至多n台_已选n台"
          style="font-size: 14px; color: #63656e"
          tag="span">
          <span
            class="number"
            style="color: #2dcb56">
            50
          </span>
          <span
            class="number"
            style="color: #3a84ff">
            {{ resultHostList.length }}
          </span>
        </I18nT>
      </template>
    </IpSelector>
    <ClusterSelector
      v-model:is-show="clusterSelectorShow"
      :cluster-types="accoutMap[accountType as keyof typeof accoutMap].clusterSelectorTypes"
      :disable-dialog-submit-method="disableClusterSubmitMethod"
      only-one-type
      :selected="selectedClusters"
      :tab-list-config="clusterTabListConfig"
      @change="handleClusterSelectorChange">
      <template #submitTips="{ clusterList: resultClusterList }">
        <I18nT
          keypath="至多n台_已选n台"
          style="font-size: 14px; color: #63656e"
          tag="span">
          <span
            class="number"
            style="color: #2dcb56">
            20
          </span>
          <span
            class="number"
            style="color: #3a84ff">
            {{ resultClusterList.length }}
          </span>
        </I18nT>
      </template>
    </ClusterSelector>
  </div>
</template>

<script setup lang="tsx">
  import { Form } from 'bkui-vue';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import SpiderModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';
  import { getWhitelist } from '@services/source/whitelist';
  import type { HostInfo } from '@services/types';

  import { AccountTypes, ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex, ipv4 } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BatchInput from './components/BatchInput.vue';
  import accoutMap from './components/common/config';
  import UserSelect from './components/UserSelect.vue';

  type SelectorModelType = TendbhaModel | TendbsingleModel | SpiderModel;

  interface Props {
    loading: boolean;
  }

  interface Emits {
    (e: 'search'): void;
    (e: 'reset'): void;
  }

  interface Expose {
    getTypes: () => {
      cluster_type: ClusterTypes;
      account_type: AccountTypes;
    };
    getUserList: () => void;
    validate: () => ReturnType<ComponentExposed<typeof Form>['validate']>;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const formData = defineModel<{
    ips: string;
    immute_domains: string;
    users: string[];
    dbs: string[];
  }>({
    required: true,
  });

  const isMaster = defineModel<boolean>('isMaster', {
    required: true,
  });

  const { t } = useI18n();
  const route = useRoute();

  const { accountType } = route.meta as { accountType: AccountTypes };
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const clusterTabListConfig = {
    tendbhaSlave: {
      name: t('高可用-从域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: ServiceParameters<typeof getTendbhaSalveList>) => {
        params.slave_domain = params.domain;
        delete params.domain;
        return getTendbhaSalveList(params);
      },
    },
    [ClusterTypes.TENDBHA]: {
      name: t('高可用-主域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: ServiceParameters<typeof getTendbhaList>) => {
        params.master_domain = params.domain;
        delete params.domain;
        return getTendbhaList(params);
      },
    },
  } as unknown as Record<string, TabConfig>;

  const rules = {
    ips: [
      {
        required: true,
        message: t('源客户端 IP 不能为空'),
        validator: (value: string) => value !== '',
      },
      {
        message: t('不支持 %'),
        validator: (value: string) => !value.includes('%'),
      },
      {
        message: t('格式错误'),
        validator: (value: string) => {
          const ipList = value.split(batchSplitRegex);
          return ipList.every((ip) => ipv4.test(ip));
        },
      },
      {
        message: t('最多输入n个', { n: 50 }),
        validator: (value: string) => {
          const ipList = value.split(batchSplitRegex);
          return ipList.length <= 50;
        },
      },
    ],
    immute_domains: [
      {
        required: true,
        message: t('域名不能为空'),
        validator: (value: string) => value !== '',
      },
      {
        message: t('格式错误'),
        validator: (value: string) => {
          const domainList = value.split(batchSplitRegex);
          return domainList.every((domain) => domainRegex.test(domain));
        },
      },
      {
        message: t('最多输入n个', { n: 20 }),
        validator: (value: string) => {
          const ipList = value.split(batchSplitRegex);
          return ipList.length <= 20;
        },
      },
    ],
  };

  const getDefaultSelectedClusters = () =>
    accoutMap[accountType as keyof typeof accoutMap].clusterSelectorTypes.reduce(
      (prevMap, type) => Object.assign({}, prevMap, { [type]: [] }),
      {},
    );

  const formRef = ref<ComponentExposed<typeof Form>>();
  const userSelectRef = ref<InstanceType<typeof UserSelect>>();
  const hostSelectorShow = ref(false);
  const clusterSelectorShow = ref(false);
  const selectedHosts = ref<HostInfo[]>([]);

  const selectedClusters = shallowRef<{ [key: string]: Array<SelectorModelType> }>(getDefaultSelectedClusters());

  const disableHostSubmitMethod = (hostList: HostInfo[]) => (hostList.length <= 50 ? false : t('至多n台', { n: 50 }));

  const disableClusterSubmitMethod = (clusterList: string[]) =>
    clusterList.length <= 20 ? false : t('至多n台', { n: 20 });

  const handleChangeIP = (data: HostInfo[]) => {
    selectedHosts.value = data;
    formData.value.ips = data.map((item) => item.ip).join(' | ');
  };

  const handleChangeWhitelist = (data: ServiceReturnType<typeof getWhitelist>['results']) => {
    // 避免与 handleChangeIP 同时修改 source_ips 参数
    nextTick(() => {
      const ipList = data.flatMap((item) => item.ips).map((ip) => ip);
      const prevIpList = formData.value.ips.split(' | ');
      formData.value.ips = [...prevIpList, ...ipList].map((item) => item).join(' | ');
    });
  };

  const handleClusterSelectorChange = (selected: Record<string, Array<SelectorModelType>>) => {
    selectedClusters.value = selected;
    const clusterList = Object.keys(selected).reduce<string[]>(
      (prevList, key) => prevList.concat(selected[key].map((item) => item.master_domain)),
      [],
    );
    formData.value.immute_domains = clusterList.join(',');
  };

  const handleDomainChange = (value: string) => {
    const newDomainList = value.split(batchSplitRegex).filter((item) => item);
    const domainMap = newDomainList.reduce<Record<string, string>>(
      (prev, domain) => Object.assign({}, prev, { [domain]: domain }),
      {},
    );
    Object.keys(selectedClusters.value).forEach((key) => {
      const clusterList = selectedClusters.value[key];
      selectedClusters.value[key] = clusterList.filter((clusterItem) => domainMap[clusterItem.master_domain]);
    });
  };

  const handleSearch = () => {
    formRef.value!.validate().then(() => {
      emits('search');
    });
  };

  const handleReset = () => {
    selectedClusters.value = getDefaultSelectedClusters();
    emits('reset');
  };

  defineExpose<Expose>({
    getTypes() {
      isMaster.value = !selectedClusters.value?.tendbhaSlave?.length;
      const clusterList = Object.values(selectedClusters.value).find((clusterList) => clusterList.length > 0);
      return {
        cluster_type: (clusterList?.[0].cluster_type || ClusterTypes.TENDBSINGLE) as ClusterTypes,
        account_type: accountType as AccountTypes,
      };
    },
    getUserList() {
      formRef.value!.validate(['ips', 'immute_domains']).then(() => {
        const clusterList = Object.values(selectedClusters.value).find((clusterList) => clusterList.length > 0);
        userSelectRef.value!.getUserList({
          ips: formData.value.ips.replace(batchSplitRegex, ','),
          immute_domains: formData.value.immute_domains.replace(batchSplitRegex, ','),
          cluster_type: (clusterList?.[0].cluster_type || ClusterTypes.TENDBSINGLE) as ClusterTypes,
          account_type: accountType as AccountTypes,
          limit: -1,
          offset: 0,
        });
      });
    },
    validate() {
      return formRef.value!.validate();
    },
  });
</script>

<style lang="less" scoped>
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
