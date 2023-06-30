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
  <div class="apply-instance">
    <DbForm
      ref="formRef"
      auto-label-width
      class="apply-form"
      :model="formdata"
      :rules="rules">
      <DbCard :title="$t('部署模块')">
        <BusinessItems
          v-model:app-abbr="formdata.details.db_app_abbr"
          v-model:biz-id="formdata.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <BkFormItem
          ref="moduleRef"
          class="is-required"
          :description="$t('表示DB的用途')"
          :label="$t('DB模块名')"
          property="details.db_module_id">
          <BkSelect
            v-model="formdata.details.db_module_id"
            class="item-input"
            :clearable="false"
            filterable
            :input-search="false"
            :loading="loading.modules"
            style="display: inline-block;">
            <BkOption
              v-for="(item) in fetchState.moduleList"
              :key="item.db_module_id"
              :label="item.name"
              :value="item.db_module_id" />
            <template #extension>
              <p
                v-bk-tooltips.top="{
                  content: $t('请先选择所属业务'),
                  disabled: !!formdata.bk_biz_id
                }">
                <BkButton
                  class="create-module"
                  :disabled="!formdata.bk_biz_id"
                  text
                  @click="handleCreateModule">
                  <i class="db-icon-plus-circle" />
                  {{ $t('新建模块') }}
                </BkButton>
              </p>
            </template>
          </BkSelect>
          <span
            v-if="formdata.bk_biz_id"
            v-bk-tooltips.top="$t('刷新获取最新DB模块名')"
            class="refresh-module"
            @click="fetchModules(Number(formdata.bk_biz_id))">
            <i class="db-icon-refresh" />
          </span>
          <div
            v-if="formdata.details.db_module_id"
            class="apply-form__database">
            <BkLoading :loading="loading.levelConfigs">
              <div v-if="fetchState.levelConfigList.length">
                <div
                  v-for="(item, index) in fetchState.levelConfigList"
                  :key="index"
                  class="apply-form__database-item">
                  <span class="apply-form__database-label">{{ item.description || item.conf_name }}:</span>
                  <span class="apply-form__database-value">{{ item.conf_value }}</span>
                </div>
              </div>
              <div
                v-else
                class="no-items">
                {{ $t('该模块暂未绑定数据库相关配置') }}
                <span
                  class="bind-module"
                  @click="handleBindConfig">{{ isBindModule ? $t('已完成') : $t('去绑定') }}</span>
              </div>
              <div
                v-if="!fetchState.levelConfigList.length"
                class="bk-form-error mt-10">
                {{ $t('需要绑定数据库相关配置') }}
              </div>
            </BkLoading>
          </div>
        </BkFormItem>
        <CloudItem
          v-model="formdata.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem v-model="formdata.details.city_code" /> -->
      <!-- <DbCard :title="$t('服务器要求')">
        <BkFormItem
          :label="$t('规格')"
          property="details.spec"
          required>
          <BkSelect
            v-model="formdata.details.spec"
            class="item-input"
            :clearable="false"
            filterable
            :loading="loading.hostSpecs">
            <BkOption
              v-for="item in fetchState.hostSpecs"
              :key="item.spec"
              :label="`${item.cpu}/${item.mem}/${item.type}`"
              :value="item.spec" />
          </BkSelect>
        </BkFormItem>
      </DbCard> -->
      <DbCard :title="$t('数据库部署信息')">
        <!-- <BkFormItem
          v-if="!isSingleType"
          :label="$t('容灾要求')"
          required>
          <BkRadio
            checked
            label="same_city_cross_zone"
            :model-value="formdata.details.disaster_tolerance_level">
            {{ $t('同城跨园区') }}
          </BkRadio>
        </BkFormItem> -->
        <BkFormItem
          v-if="!isSingleType"
          :label="$t('Proxy起始端口')"
          property="details.start_proxy_port"
          required>
          <BkInput
            v-model="formdata.details.start_proxy_port"
            class="inline-box"
            :max="65535"
            :min="1025"
            type="number" />
          <span class="apply-form__tips ml-10">{{ $t('多集群部署时_系统将从起始端口开始自动分配') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="$t('MySQL起始端口')"
          property="details.start_mysql_port"
          required>
          <BkInput
            v-model="formdata.details.start_mysql_port"
            class="inline-box"
            :max="65535"
            :min="1025"
            type="number" />
          <span
            v-if="isSingleType"
            class="apply-form__tips ml-10">{{ $t('多实例部署时_系统将从起始端口开始自动分配') }}</span>
          <span
            v-else
            class="apply-form__tips ml-10">{{ $t('多集群部署时_系统将从起始端口开始自动分配') }}</span>
        </BkFormItem>
      </DbCard>
      <DbCard :title="$t('需求信息')">
        <BkFormItem
          :label="formItemLabels.clusterCount"
          property="details.cluster_count"
          required>
          <BkInput
            v-model="formdata.details.cluster_count"
            class="inline-box"
            :min="1"
            :placeholder="$t('请输入')"
            type="number"
            @blur="handleCalcIps"
            @change="handleChangeClusterCount" />
        </BkFormItem>
        <BkFormItem
          :label="formItemLabels.instNums"
          property="details.inst_num"
          required>
          <BkInput
            v-model="formdata.details.inst_num"
            class="inline-box"
            :max="formdata.details.cluster_count"
            :min="1"
            type="number"
            @blur="handleCalcIps" />
        </BkFormItem>
        <BkFormItem
          class="service"
          :label="$t('域名设置')"
          required>
          <DomainTable
            v-model:domains="formdata.details.domains"
            :formdata="formdata"
            :module-name="moduleName"
            :ticket-type="type" />
        </BkFormItem>
        <BkFormItem
          :label="$t('服务器选择')"
          property="details.ip_source"
          required>
          <BkRadioGroup
            v-model="formdata.details.ip_source">
            <BkRadioButton
              label="resource_pool"
              style="width: 218px;">
              {{ $t('自动从资源池匹配') }}
            </BkRadioButton>
            <BkRadioButton
              label="manual_input"
              style="width: 218px;">
              {{ $t('手动录入IP') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <Transition
          mode="out-in"
          name="dbm-fade">
          <div
            v-if="formdata.details.ip_source === 'manual_input'"
            class="mb-24">
            <DbFormItem
              v-if="!isSingleType"
              ref="proxyRef"
              label="Proxy"
              property="details.nodes.proxy"
              required>
              <IpSelector
                :biz-id="formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formdata.details.nodes.proxy"
                :disable-dialog-submit-method="disableHostSubmitMethods.proxy"
                :disable-host-method="proxyDisableHostMethod"
                @change="handleProxyIpChange">
                <template #desc>
                  {{ $t('需n台', { n: hostNums }) }}
                </template>
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="需n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> {{ hostNums }} </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
              </IpSelector>
            </DbFormItem>
            <DbFormItem
              ref="backendRef"
              :label="formItemLabels.backend"
              property="details.nodes.backend"
              required>
              <IpSelector
                :biz-id="formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formdata.details.nodes.backend"
                :disable-dialog-submit-method="disableHostSubmitMethods.backend"
                :disable-host-method="backendDisableHostMethod"
                @change="handleBackendIpChange">
                <template #desc>
                  {{ $t('需n台', { n: hostNums }) }}
                </template>
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="需n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> {{ hostNums }} </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
              </IpSelector>
            </DbFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              v-if="isSingleType"
              :label="$t('后端存储资源规格')"
              property="details.resource_spec.single.spec_id"
              required>
              <SpecSelector
                ref="specSingleRef"
                v-model="formdata.details.resource_spec.single.spec_id"
                :cluster-type="ClusterTypes.TENDBSINGLE"
                machine-type="single"
                style="width: 435px;" />
            </BkFormItem>
            <template v-else>
              <BkFormItem
                :label="$t('Proxy存储资源规格')"
                property="details.resource_spec.proxy.spec_id"
                required>
                <SpecSelector
                  ref="specProxyRef"
                  v-model="formdata.details.resource_spec.proxy.spec_id"
                  :cluster-type="ClusterTypes.TENDBHA"
                  machine-type="proxy"
                  style="width: 435px;" />
              </BkFormItem>
              <BkFormItem
                :label="$t('后端存储资源规格')"
                property="details.resource_spec.backend.spec_id"
                required>
                <SpecSelector
                  ref="specBackendRef"
                  v-model="formdata.details.resource_spec.backend.spec_id"
                  :cluster-type="ClusterTypes.TENDBHA"
                  machine-type="backend"
                  style="width: 435px;" />
              </BkFormItem>
            </template>
          </div>
        </Transition>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="formdata.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px;"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
    <div class="absolute-footer">
      <BkButton
        :loading="baseState.isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <BkButton @click="handleShowPreview">
        {{ $t('预览') }}
      </BkButton>
      <BkButton
        :disabled="baseState.isSubmitting"
        @click="handleResetFormdata">
        {{ $t('重置') }}
      </BkButton>
      <BkButton
        :disabled="baseState.isSubmitting"
        @click="handleCancel">
        {{ $t('取消') }}
      </BkButton>
    </div>
    <!-- 预览功能 -->
    <BkDialog
      v-model:is-show="isShowPreview"
      header-position="left"
      :height="624"
      :width="1180">
      <template #header>
        {{ $t('实例预览') }}
        <span class="apply-dialog__quantity">{{ $t('共n条', { n: formdata.details.cluster_count }) }}</span>
      </template>
      <PreviewTable
        :data="previewData"
        :is-show-nodes="formdata.details.ip_source === 'manual_input'"
        :is-single-type="isSingleType"
        :nodes="previewNodes" />
      <template #footer>
        <BkButton
          @click="() => isShowPreview = false">
          {{ $t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { BizItem, ModuleItem } from '@services/types/common';
  import type { HostDetails } from '@services/types/ip';
  import type { HostSpec } from '@services/types/ticket';

  import { useApplyBase } from '@hooks';

  import {
    ClusterTypes,
    mysqlType,
    type MysqlTypeString,
    TicketTypes,
  } from '@common/const';
  import { nameRegx } from '@common/regex';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import DomainTable from './components/MySQLDomainTable.vue';
  import PreviewTable from './components/PreviewTable.vue';
  import { useMysqlData } from './hooks/useMysqlData';

  const props = defineProps({
    type: {
      type: String,
      required: true,
    },
  });

  // 基础设置
  const {
    baseState,
    bizState,
    handleCancel,
    handleCreateAppAbbr,
    handleCreateTicket,
  } = useApplyBase();

  const { t } = useI18n();
  const router = useRouter();

  const specProxyRef = ref();
  const specBackendRef = ref();
  const specSingleRef = ref();
  const backendRef = ref();
  const proxyRef = ref();
  const moduleRef = ref();
  const isBindModule = ref(false);
  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const rules = computed(() => ({
    'details.db_app_abbr': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (val: string) => nameRegx.test(val),
      },
    ],
    'details.db_module_id': [
      {
        message: t('请先选择所属业务'),
        trigger: 'blur',
        validator: () => !!formdata.bk_biz_id,
      },
      {
        message: t('DB模块名不能为空'),
        trigger: 'blur',
        validator: (val: number) => !!val,
      },
    ],
    'details.nodes.proxy': [{
      message: t('请添加服务器'),
      trigger: 'change',
      validator: () => {
        const counts = formdata.details.nodes.proxy.length;
        return counts !== 0;
      },
    }],
    'details.nodes.backend': [{
      message: t('请添加服务器'),
      trigger: 'change',
      validator: () => {
        const counts = formdata.details.nodes.backend.length;
        return counts !== 0;
      },
    }],
  }));
  const isSingleType = computed(() => props.type === TicketTypes.MYSQL_SINGLE_APPLY);
  const formItemLabels = computed(() => {
    const labels = {
      clusterCount: t('集群数量'),
      backend: 'Master \\ Slave',
      instNums: t('每组主机部署集群数量'),
    };
    if (isSingleType.value) {
      labels.clusterCount = t('实例数量');
      labels.backend = t('服务器');
      labels.instNums = t('每台主机部署实例数量');
    }
    return labels;
  });
  const hostSpecInfo = computed(() => (
    fetchState.hostSpecs.find((info: HostSpec) => info.spec === formdata.details.spec)
  ));
  const typeInfo = computed(() => mysqlType[props.type as MysqlTypeString]);
  const moduleName = computed(() => {
    const item = fetchState.moduleList.find((item: ModuleItem) => item.db_module_id === formdata.details.db_module_id);
    return item?.name ?? '';
  });
  const tableData = computed(() => {
    if (moduleName.value && (formdata.details.db_app_abbr)) {
      return formdata.details.domains;
    }
    return [];
  });
  const hostNums = computed(() => {
    const { cluster_count: clusterCount, inst_num: instCount } = formdata.details;
    if (clusterCount <= 0 || instCount <= 0) return 0;
    const nums = Math.ceil(clusterCount / instCount);
    return isSingleType.value ? nums : nums * 2;
  });

  // 获取基础数据信息
  const {
    formdata,
    fetchState,
    loading,
    leveConfig,
    handleResetFormdata,
    fetchModules,
    fetchLevelConfig,
  } = useMysqlData(props.type);

  function handleChangeClusterCount(value: number) {
    if (value && formdata.details.inst_num > value) {
      formdata.details.inst_num = value;
    }
  }

  /**
   * 变更业务选择
   */
  function handleChangeBiz(info: BizItem) {
    formdata.details.db_module_id = null;
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formdata.details.nodes.backend = [];
    formdata.details.nodes.proxy = [];
    moduleRef.value?.clearValidate();
  }

  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formdata.details.nodes.backend = [];
    formdata.details.nodes.proxy = [];
  }

  function handleCalcIps() {
    nextTick(() => {
      const { backend, proxy } = formdata.details.nodes;
      if (hostNums.value < backend.length) {
        formdata.details.nodes.backend.splice(hostNums.value);
      }
      if (hostNums.value < proxy.length) {
        formdata.details.nodes.proxy.splice(hostNums.value);
      }
    });
  }

  const disableHostSubmitMethods = {
    proxy: (hostList: Array<any>) => (hostList.length !== hostNums.value ? t('xx共需n台', { title: 'Proxy', n: hostNums.value }) : false),
    backend: (hostList: Array<any>) => (hostList.length !== hostNums.value ? t('xx共需n台', { title: 'Master \\ Slave', n: hostNums.value }) : false),
  };
  const makeMapByHostId = (hostList: Array<HostDetails>) => hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  // proxy、backend 节点互斥
  function proxyDisableHostMethod(data: any, list: any[]) {
    const masterHostMap = makeMapByHostId(formdata.details.nodes.backend);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master_Slave使用');
    }

    if (list.length >= hostNums.value && !list.find(item => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [hostNums.value, list.length]);
    }

    return false;
  }

  function backendDisableHostMethod(data: any, list: any[]) {
    const masterHostMap = makeMapByHostId(formdata.details.nodes.proxy);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }

    if (list.length >= hostNums.value && !list.find(item => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [hostNums.value, list.length]);
    }

    return false;
  }

  /**
   * 更新 Proxy IP
   */
  function handleProxyIpChange(data: HostDetails[]) {
    formdata.details.nodes.proxy = [...data];
    if (formdata.details.nodes.proxy.length > 0) {
      proxyRef.value.clearValidate();
    }
  }

  /**
   * 更新 Backend
   */
  function handleBackendIpChange(data: HostDetails[]) {
    formdata.details.nodes.backend = [...data];
    if (formdata.details.nodes.backend.length > 0) {
      backendRef.value.clearValidate();
    }
  }

  /** 获取版本、字符集信息 */
  watch(() => fetchState.levelConfigList, (value) => {
    value.forEach((item) => {
      Object.keys(leveConfig).forEach((key) => {
        if (key === item.conf_name) {
          if (item.conf_value !== undefined) leveConfig[key] = item.conf_value;
        }
      });
    });
  });

  /**
   * 预览功能
   */
  const previewNodes = computed(() => ({
    proxy: formatNodes(formdata.details.nodes.proxy),
    backend: formatNodes(formdata.details.nodes.backend),
  }));
  const previewData = computed(() => tableData.value.map(({ key }: { key: string }) => ({
    domain: `${moduleName.value}db.${key}.${formdata.details.db_app_abbr}.db`,
    slaveDomain: `${moduleName.value}db.${key}.${formdata.details.db_app_abbr}.db`,
    disasterDefence: t('同城跨园区'),
    deployStructure: typeInfo.value.name,
    version: leveConfig.db_version,
    charset: leveConfig.charset,
    spec: hostSpecInfo.value ? `${hostSpecInfo.value.cpu}/${hostSpecInfo.value.mem}` : '',
  })));
  const isShowPreview = ref(false);
  const handleShowPreview = () => {
    isShowPreview.value = true;
  };

  /**
   * 格式化 IP 提交格式
   */
  function formatNodes(hosts: HostDetails[]) {
    return hosts.map(host => ({
      ip: host.ip,
      bk_host_id: host.host_id,
      bk_cloud_id: host.cloud_id,
      bk_biz_id: host.biz.id,
    }));
  }

  /**
   * 提交申请
   */
  const formRef = ref();
  const handleSubmit = async () => {
    const validate = await formRef.value?.validate()
      .then(() => true)
      .catch(() => false);
    if (validate && fetchState.levelConfigList.length) {
      baseState.isSubmitting = true;

      const getDetails = () => {
        const details: Record<string, any> = { ...markRaw(formdata.details) };

        if (formdata.details.ip_source === 'resource_pool') {
          delete details.nodes;
          if (isSingleType.value) {
            return {
              ...details,
              resource_spec: {
                single: {
                  ...details.resource_spec.single,
                  ...specSingleRef.value.getData(),
                  count: hostNums.value,
                },
              },
            };
          }

          return {
            ...details,
            resource_spec: {
              proxy: {
                ...details.resource_spec.proxy,
                ...specProxyRef.value.getData(),
                count: hostNums.value,
              },
              backend: {
                ...details.resource_spec.backend,
                ...specBackendRef.value.getData(),
                count: hostNums.value,
              },
            },
          };
        }

        delete details.resource_spec;
        return {
          ...details,
          nodes: {
            proxy: formatNodes(formdata.details.nodes.proxy),
            backend: formatNodes(formdata.details.nodes.backend),
          },
        };
      };

      const params = {
        ...formdata,
        details: getDetails(),
      };
      // 如果英文名为空新增业务英文名称接口，创建单据
      bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
    }
  };

  /**
   * 新建模块
   */
  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'SelfServiceCreateDbModule',
      params: {
        type: props.type,
        bk_biz_id: formdata.bk_biz_id,
      },
    });
    window.open(url.href, '_blank');
  };

  const handleBindConfig = () => {
    if (isBindModule.value) {
      fetchLevelConfig(formdata.details.db_module_id as number);
      return;
    }
    const moduleInfo = fetchState.moduleList.find(item => item.db_module_id ===  formdata.details.db_module_id);
    const moduleName = moduleInfo?.name ?? '';
    const moduleNameQuery = moduleName ? { module_name: moduleName } : {};
    isBindModule.value = true;
    const url = router.resolve({
      name: 'SelfServiceBindDbModule',
      params: {
        type: props.type,
        bk_biz_id: formdata.bk_biz_id,
        db_module_id: formdata.details.db_module_id,
      },
      query: { ...moduleNameQuery },
    });
    window.open(url.href, '_blank');
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";
  @import "@styles/applyInstance.less";

  :deep(.domain-address) {
    .flex-center();

    > span {
      flex-shrink: 0;
    }

    &__item {
      margin-bottom: 0;

      .bk-form-label {
        display: none;
      }
    }

    &__placeholder {
      min-width: 12px;
    }
  }

  :deep(.item-input) {
    width: 435px;
  }

  .service-table {
    max-width: 932px !important;

    :deep(.bk-table-body) {
      max-height: 350px;
    }
  }

  .apply-form {
    &__database {
      width: 398px;
      padding: 8px 12px;
      margin-top: 16px;
      font-size: @font-size-mini;
      line-height: 20px;
      background-color: @bg-gray;
      border-radius: 2px;

      .no-items {
        text-align: center;

        .bind-module {
          color: @primary-color;
          cursor: pointer;
        }
      }

      &-label {
        display: inline-block;
        min-width: 100px;
        padding-right: 8px;
        text-align: right;
      }

      &-value {
        color: @title-color;
      }
    }
  }

  .deploy-group {
    .bk-popover {
      display: inline-block;
    }

    :deep(.bk-radio-text) {
      border-bottom: 1px dashed #979ba5;
    }
  }

  .create-module {
    display: block;
    width: 100%;
    padding: 0 8px;
    text-align: left;

    .db-icon-plus-circle {
      margin-right: 4px;
    }

    &:hover:not(.is-disabled) {
      color: @primary-color;
    }
  }

  .refresh-module {
    margin-left: 8px;
    font-size: @font-size-normal;
    color: @primary-color;
    vertical-align: middle;
    cursor: pointer;
  }

  .apply-dialog {
    &__quantity {
      margin-left: 15px;
      font-size: @font-size-normal;
      color: @default-color;
    }
  }
</style>
