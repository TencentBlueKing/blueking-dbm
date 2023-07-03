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
      :model="state.formdata"
      :rules="rules">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:app-abbr="state.formdata.details.db_app_abbr"
          v-model:biz-id="state.formdata.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <ClusterName v-model="state.formdata.details.cluster_name" />
        <ClusterAlias v-model="state.formdata.details.cluster_alias" />
        <CloudItem
          v-model="state.formdata.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem
        v-model="state.formdata.details.city_code"
        @change="handleChangeCityCode" /> -->
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('部署架构')"
          property="details.cluster_type"
          required>
          <BkRadioGroup
            v-model="state.formdata.details.cluster_type"
            class="item-input"
            @change="handleChangeClusterType">
            <BkPopover
              v-for="item of Object.values(redisClusterTypes)"
              :key="item.id"
              placement="top"
              theme="light"
              trigger="hover">
              <BkRadioButton :label="item.id">
                {{ item.text }}
              </BkRadioButton>
              <template #content>
                <div class="apply-instance__content">
                  <h4>{{ item.tipContent.title }}</h4>
                  <p>{{ item.tipContent.desc }}</p>
                  <img
                    :src="item.tipContent.img"
                    width="550">
                </div>
              </template>
            </BkPopover>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="$t('版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="state.formdata.details.db_version"
            class="item-input"
            :clearable="false"
            filterable
            :input-search="false"
            :list="state.versions"
            :loading="state.isLoadVersion" />
        </BkFormItem>
        <BkFormItem
          :label="$t('服务器选择')"
          property="details.ip_source"
          required>
          <BkRadioGroup
            v-model="state.formdata.details.ip_source"
            class="item-input"
            @change="fetchCapSpecs(state.formdata.details.city_code)">
            <BkRadioButton
              v-for="item of Object.values(redisIpSources)"
              :key="item.id"
              v-bk-tooltips="{
                content: $t('该功能暂未开放'),
                disabled: !item.disabled
              }"
              :disabled="item.disabled"
              :label="item.id">
              {{ item.text }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <Transition
          mode="out-in"
          name="dbm-fade">
          <div
            v-if="isManualInput"
            class="mb-24">
            <DbFormItem
              label="Proxy"
              property="details.nodes.proxy"
              required>
              <IpSelector
                :biz-id="state.formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="state.formdata.details.nodes.proxy"
                :disable-dialog-submit-method="ipSelectorDisableSubmitMethods.proxy"
                :disable-host-method="proxyDisableHostMethod"
                @change="handleProxyIpChange">
                <template #desc>
                  {{ $t('至少n台', { n: 2 }) }}
                </template>
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> 2 </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
              </IpSelector>
            </DbFormItem>
            <BkFormItem
              v-if="state.formdata.details.nodes.proxy.length > 0"
              label="">
              <div class="apply-instance__inline">
                <BkFormItem
                  :label="$t('Proxy端口')"
                  label-width="110"
                  property="details.proxy_port"
                  required>
                  <BkInput
                    v-model="state.formdata.details.proxy_port"
                    :max="65535"
                    :min="1025"
                    style="width: 120px;"
                    type="number" />
                  <span class="ml-16">{{ $t('从n起', { n: state.formdata.details.proxy_port }) }}</span>
                </BkFormItem>
              </div>
            </BkFormItem>
            <DbFormItem
              ref="masterRef"
              label="Master"
              property="details.nodes.master"
              required>
              <IpSelector
                :biz-id="state.formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="state.formdata.details.nodes.master"
                :disable-dialog-submit-method="ipSelectorDisableSubmitMethods.master"
                :disable-host-method="masterDisableHostMethod"
                @change="handleMasterIpChange">
                <template #desc>
                  {{ $t('至少1台_且机器数要和Slave相等') }}
                </template>
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> 1 </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
              </IpSelector>
            </DbFormItem>
            <DbFormItem
              ref="slaveRef"
              label="Slave"
              property="details.nodes.slave"
              required>
              <IpSelector
                :biz-id="state.formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="state.formdata.details.nodes.slave"
                :disable-dialog-submit-method="ipSelectorDisableSubmitMethods.slave"
                :disable-host-method="slaveDisableHostMethod"
                @change="handleSlaveIpChange">
                <template #desc>
                  {{ $t('至少1台_且机器数要和Master相等') }}
                </template>
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> 1 </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
              </IpSelector>
            </DbFormItem>
            <!-- 保留了资源池显示后的逻辑，后续确认不需要可以去掉 -->
            <BkFormItem
              :label="isManualInput ? $t('总容量') : $t('申请容量')"
              property="details.cap_key"
              required>
              <div
                :key="capSpecsKey"
                v-bk-tooltips="{
                  disabled: !disableCapSpecs,
                  content: $t('请确保Master和Slave的机器数量至少1台且机器数要相等')
                }"
                class="item-input">
                <BkSelect
                  v-model="state.formdata.details.cap_key"
                  class="item-input"
                  :clearable="false"
                  :disabled="disableCapSpecs"
                  filterable
                  :input-search="false"
                  :loading="state.isLoadCapSpecs">
                  <BkOption
                    v-for="item of state.capSpecs"
                    :key="item.cap_key"
                    :label="getDispalyCapSpecs(item)"
                    :value="item.cap_key" />
                </BkSelect>
              </div>
              <p
                v-if="isManualInput"
                class="apply-form__tips">
                {{ $t('单实例容量x分片数_根据选择的主机自动计算所有的组合') }}
              </p>
            </BkFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              :label="$t('Proxy规格')"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="$t('规格')"
                  property="details.resource_spec.proxy.spec_id"
                  required>
                  <SpecSelector
                    ref="specProxyRef"
                    v-model="state.formdata.details.resource_spec.proxy.spec_id"
                    :cluster-type="typeInfos.cluster_type"
                    :machine-type="typeInfos.machine_type" />
                </BkFormItem>
                <BkFormItem
                  :label="$t('数量')"
                  property="details.resource_spec.proxy.count"
                  required>
                  <BkInput
                    v-model="state.formdata.details.resource_spec.proxy.count"
                    :min="2"
                    type="number" />
                  <span class="input-desc">{{ $t('至少n台', {n: 2}) }}</span>
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="$t('部署方案')"
              property="details.resource_plan.resource_plan_id"
              required>
              <PlanSelector
                v-model="state.formdata.details.resource_plan"
                :cluster-type="typeInfos.cluster_type"
                :machine-type="typeInfos.backend_machine_type" />
            </BkFormItem>
          </div>
        </Transition>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="state.formdata.remark"
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
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getCapSpecs } from '@services/ticket';
  import type { BizItem } from '@services/types/common';
  import type { HostDetails } from '@services/types/ip';
  import type { CapSepcs } from '@services/types/ticket';
  import { getVersions } from '@services/versionFiles';

  import { useApplyBase, useInfo  } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';
  import { nameRegx } from '@common/regex';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import PlanSelector from '@components/apply-items/PlanSelector.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import { generateId } from '@utils';

  import { redisClusterTypes, redisIpSources } from './common/const';

  type Version = {
    value: string,
    label: string,
  }

  // 基础设置
  const {
    baseState,
    bizState,
    handleCancel,
    handleCreateAppAbbr,
    handleCreateTicket,
  } = useApplyBase();

  const { t } = useI18n();
  const masterRef = ref();
  const slaveRef = ref();
  const specProxyRef = ref();
  const capSpecsKey  = ref(generateId('CLUSTER_APPLAY_CAP_'));

  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const state = reactive({
    formdata: initData(),
    isLoadVersion: false,
    versions: [] as Version[],
    isLoadCapSpecs: false,
    capSpecs: [] as CapSepcs[],
  });
  const rules = {
    'details.cluster_name': [{
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'blur',
      validator: (val: string) => nameRegx.test(val),
    }],
    'details.nodes.proxy': [
      {
        message: t('Proxy数量至少为2台'),
        trigger: 'change',
        validator: (value: HostDetails[]) => value.length >= 2,
      },
    ],
    'details.nodes.master': [
      {
        message: t('Master数量至少为1台_且机器数要和Slave相等'),
        trigger: 'change',
        validator: (value: HostDetails[]) => (
          value.length > 0
          && state.formdata.details.nodes.slave.length === value.length
        ),
      },
    ],
    'details.nodes.slave': [
      {
        message: t('Slave数量至少为1台_且机器数要和Master相等'),
        trigger: 'change',
        validator: (value: HostDetails[]) => (
          value.length > 0
          && state.formdata.details.nodes.master.length === value.length
        ),
      },
    ],
  };
  const isManualInput = computed(() => state.formdata.details.ip_source === redisIpSources.manual_input.id);
  const disableCapSpecs = computed(() => {
    const { master, slave } = state.formdata.details.nodes;
    // 资源池模式不需要判断
    if (!isManualInput.value) return false;
    return master.length === 0 || master.length !== slave.length;
  });
  const typeInfos = computed(() => {
    const types = {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        cluster_type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        machine_type: 'twemproxy',
        backend_machine_type: 'tendiscache',
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        cluster_type: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        machine_type: 'twemproxy',
        backend_machine_type: 'tendisssd',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        cluster_type: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        machine_type: 'predixy',
        backend_machine_type: 'tendisplus',
      },
    };
    return types[state.formdata.details.cluster_type as keyof typeof types];
  });

  /** 初始化数据 */
  function initData() {
    return {
      bk_biz_id: '' as number | '',
      ticket_type: TicketTypes.REDIS_CLUSTER_APPLY,
      remark: '',
      details: {
        bk_cloud_id: '',
        db_app_abbr: '',
        proxy_port: 50000,
        cluster_name: '',
        cluster_alias: '',
        cluster_type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        city_code: '',
        db_version: '',
        cap_key: '',
        ip_source: redisIpSources.manual_input.id,
        nodes: {
          proxy: [] as HostDetails[],
          master: [] as HostDetails[],
          slave: [] as HostDetails[],
        },
        resource_spec: {
          proxy: {
            spec_id: '',
            count: 2,
          },
        },
        resource_plan: {
          resource_plan_name: '',
          resource_plan_id: '',
        },
      },
    };
  }

  function getDispalyCapSpecs(item: CapSepcs) {
    if (state.formdata.details.cluster_type === ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE) {
      return `${item.total_disk}(${item.max_disk} GB x ${item.shard_num}${t('分片')})`;
    }
    return `${item.total_memory}(${getMaxMemoryToGb(item.maxmemory)} x ${item.shard_num}${t('分片')})`;
  }

  /**
   * 单实例容量转为 GB
   */
  function getMaxMemoryToGb(mem: number) {
    return `${(mem / 1024).toFixed(1)} GB`;
  }

  /**
   * 获取 redis 版本信息
   */
  function fetchVersions(queryKey: string) {
    state.isLoadVersion = true;
    getVersions({ query_key: queryKey })
      .then((res) => {
        state.versions = res.map(value => ({ value, label: value }));
      })
      .finally(() => {
        state.isLoadVersion = false;
      });
  }
  fetchVersions(state.formdata.details.cluster_type);

  /**
   * 获取 redis 容量信息
   */
  function fetchCapSpecs(cityCode: string) {
    state.formdata.details.cap_key = '';
    const { master, slave } = state.formdata.details.nodes;
    if (isManualInput.value && (master.length === 0 || master.length !== slave.length)) {
      return;
    }
    state.isLoadCapSpecs = true;
    getCapSpecs(cityCode, {
      cluster_type: state.formdata.details.cluster_type,
      ip_source: state.formdata.details.ip_source,
      nodes: {
        master: formatNodes(master),
        slave: formatNodes(slave),
      },
    })
      .then((res) => {
        state.capSpecs = res;
        const suggestItem = res.find(item => item.selected);
        if (suggestItem) {
          state.formdata.details.cap_key = suggestItem.cap_key;
        } else if (res.length > 0) {
          state.formdata.details.cap_key = res[0].cap_key;
        }
      })
      .finally(() => {
        state.isLoadCapSpecs = false;
      });
  }

  function handleChangeClusterType(value: string) {
    state.formdata.details.db_version = '';
    state.formdata.details.resource_spec.proxy.spec_id = '';
    fetchVersions(value);
    isManualInput.value && fetchCapSpecs('');
  }

  /**
   * 变更业务
   */
  function handleChangeBiz(info: BizItem) {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    // 清空 ip 选择器
    state.formdata.details.nodes.proxy = [];
    state.formdata.details.nodes.master = [];
    state.formdata.details.nodes.slave = [];
  }

  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    // 清空 ip 选择器
    state.formdata.details.nodes.proxy = [];
    state.formdata.details.nodes.master = [];
    state.formdata.details.nodes.slave = [];
  }

  /** 重置表单 */
  function handleResetFormdata() {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        state.formdata = initData();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  }

  const ipSelectorDisableSubmitMethods = {
    proxy: (hostList: Array<any>) => (hostList.length >= 2 ? false : t('至少n台', { n: 2 })),
    master: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
    slave: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
  };

  const makeMapByHostId = (hostList: Array<HostDetails>) => hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  // proxy、master、slave 互斥
  function proxyDisableHostMethod(data: any) {
    const masterHostMap = makeMapByHostId(state.formdata.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master使用');
    }
    const slaveHostMap = makeMapByHostId(state.formdata.details.nodes.slave);
    if (slaveHostMap[data.host_id]) {
      return t('主机已被Slave使用');
    }

    return false;
  }

  // proxy、master、slave 互斥
  function masterDisableHostMethod(data: any) {
    const proxyHostMap = makeMapByHostId(state.formdata.details.nodes.proxy);
    if (proxyHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }
    const slaveHostMap = makeMapByHostId(state.formdata.details.nodes.slave);
    if (slaveHostMap[data.host_id]) {
      return t('主机已被Slave使用');
    }

    return false;
  }
  // proxy、master、slave 互斥
  function slaveDisableHostMethod(data: any) {
    const proxyHostMap = makeMapByHostId(state.formdata.details.nodes.proxy);
    if (proxyHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }
    const masterHostMap = makeMapByHostId(state.formdata.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master使用');
    }

    return false;
  }

  /**
   * 更新 Proxy IP
   */
  function handleProxyIpChange(data: HostDetails[]) {
    state.formdata.details.nodes.proxy = [...data];
  }

  /**
   * 更新 Master IP
   */
  function handleMasterIpChange(data: HostDetails[]) {
    state.formdata.details.nodes.master = [...data];
    fetchCapSpecs(state.formdata.details.city_code);
    masterRef.value?.validate?.();
    slaveRef.value?.validate?.();
    capSpecsKey.value = generateId('CLUSTER_APPLAY_CAP_');
  }

  /**
   * 更新 Slave IP
   */
  function handleSlaveIpChange(data: HostDetails[]) {
    state.formdata.details.nodes.slave = [...data];
    fetchCapSpecs(state.formdata.details.city_code);
    masterRef.value?.validate?.();
    slaveRef.value?.validate?.();
    capSpecsKey.value = generateId('CLUSTER_APPLAY_CAP_');
  }

  /**
   * 格式化 IP 提交格式
   */
  function formatNodes(hosts: HostDetails[]) {
    return hosts.map(host => ({
      ip: host.ip,
      bk_host_id: host.host_id,
      bk_cloud_id: host.cloud_id,
      bk_cpu: host.bk_cpu,
      bk_disk: host.bk_disk,
      bk_mem: host.bk_mem,
      bk_biz_id: host.biz.id,
    }));
  }

  const formRef = ref();
  async function handleSubmit() {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const details: Record<string, any> = { ...markRaw(state.formdata.details) };

      if (state.formdata.details.ip_source === 'resource_pool') {
        delete details.nodes;

        return {
          ...details,
          resource_spec: {
            proxy: {
              ...details.resource_spec.proxy,
              ...specProxyRef.value.getData(),
              count: Number(details.resource_spec.proxy.count),
              spec_cluster_type: typeInfos.value.cluster_type,
              spec_machine_type: typeInfos.value.machine_type,
            },
          },
        };
      }

      delete details.resource_spec;
      delete details.resource_plan;
      return {
        ...details,
        nodes: {
          proxy: formatNodes(state.formdata.details.nodes.proxy),
          master: formatNodes(state.formdata.details.nodes.master),
          slave: formatNodes(state.formdata.details.nodes.slave),
        },
      };
    };
    const params = {
      ...state.formdata,
      details: getDetails(),
    };
    // 若业务没有英文名称则先创建业务英文名称再创建单据，反正直接创建单据
    bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
  }
</script>

<style lang="less" scoped>
  @import "@styles/applyInstance.less";

  .apply-instance {
    .bk-radio-group {
      display: inline-flex;

      :deep(.bk-radio-button) {
        flex: 1;
      }
    }

    :deep(.item-input) {
      width: 462px;
    }

    &__inline {
      width: 396px;
      padding: 8px 0;
      font-size: @font-size-mini;
      background-color: #f5f7fa;
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    .resource-pool-item {
      width: 655px;
      padding: 24px 0;
      background-color: #F5F7FA;
      border-radius: 2px;

      .bk-form-item {
        .bk-form-label {
          width: 120px !important;
        }

        .bk-form-content {
          margin-left: 120px !important;

          .bk-select,
          .bk-input {
            width: 314px;
          }
        }
      }
    }
  }

  .apply-instance__content {
    max-width: 550px;

    h4 {
      padding: 8px 0;
      font-size: 14px;
      color: @title-color;
    }

    p {
      padding-bottom: 12px;
      color: @default-color;
    }
  }
</style>
