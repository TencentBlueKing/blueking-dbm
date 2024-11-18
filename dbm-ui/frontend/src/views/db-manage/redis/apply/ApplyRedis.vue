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
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <div class="apply-instance">
      <DbForm
        ref="formRef"
        class="apply-form"
        :label-width="200"
        :model="state.formdata"
        :rules="rules">
        <DbCard :title="t('业务信息')">
          <BusinessItems
            v-model:app-abbr="state.formdata.details.db_app_abbr"
            v-model:biz-id="state.formdata.bk_biz_id"
            perrmision-action-id="redis_cluster_apply"
            @change-biz="handleChangeBiz" />
          <ClusterName v-model="state.formdata.details.cluster_name" />
          <ClusterAlias
            v-model="state.formdata.details.cluster_alias"
            :biz-id="state.formdata.bk_biz_id"
            cluster-type="redis" />
          <CloudItem
            v-model="state.formdata.details.bk_cloud_id"
            @change="handleChangeCloud" />
        </DbCard>
        <RegionItem
          ref="regionItemRef"
          v-model="state.formdata.details.city_code" />
        <DbCard :title="t('数据库部署信息')">
          <AffinityItem
            v-model="state.formdata.details.resource_spec.backend_group.affinity"
            :city-code="state.formdata.details.city_code" />
        </DbCard>
        <DbCard :title="t('部署需求')">
          <BkFormItem
            :label="t('部署架构')"
            property="details.cluster_type"
            required>
            <BkRadioGroup
              v-model="state.formdata.details.cluster_type"
              class="item-input"
              @change="handleChangeClusterType">
              <BkPopover
                v-for="item of renderRedisClusterTypes"
                :key="item.id"
                placement="top"
                :popover-delay="0"
                theme="light"
                trigger="hover">
                <BkRadioButton :label="item.id">
                  {{ item.text }}
                </BkRadioButton>
                <template #content>
                  <div class="apply-instance-content">
                    <h4>{{ item.tipContent.title }}</h4>
                    <p>{{ item.tipContent.title }}：{{ item.tipContent.desc }}</p>
                    <img
                      :src="item.tipContent.img"
                      width="550" />
                  </div>
                </template>
              </BkPopover>
            </BkRadioGroup>
            <BkButton
              class="recommend-architectrue-btn ml-10"
              text
              theme="primary"
              @click="handleRecommendArchitectrueOpen">
              {{ t('如何选择架构？') }}
            </BkButton>
          </BkFormItem>
          <BkFormItem
            :label="t('版本')"
            property="details.db_version"
            required>
            <DeployVersion
              v-model="state.formdata.details.db_version"
              db-type="redis"
              :query-key="typeInfos.pkg_type" />
          </BkFormItem>
          <BkFormItem
            :label="t('访问密码')"
            property="details.proxy_pwd"
            required>
            <PasswordInput
              ref="passwordRef"
              v-model="state.formdata.details.proxy_pwd"
              :db-type="DBTypes.REDIS" />
          </BkFormItem>
          <BkFormItem
            :label="t('服务器选择')"
            property="details.ip_source"
            required>
            <BkRadioGroup
              v-model="state.formdata.details.ip_source"
              class="item-input"
              @change="fetchCapSpecs(state.formdata.details.city_code)">
              <!-- 暂时去掉手动录入IP -->
              <BkRadioButton
                :key="redisIpSources.resource_pool.id"
                :label="redisIpSources.resource_pool.id">
                {{ redisIpSources.resource_pool.text }}
              </BkRadioButton>
              <!-- <BkRadioButton
                v-for="item of Object.values(redisIpSources)"
                :key="item.id"
                :label="item.id">
                {{ item.text }}
              </BkRadioButton> -->
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
                  :os-types="[OSTypes.Linux]"
                  @change="handleProxyIpChange">
                  <template #desc>
                    {{ t('至少n台', { n: 2 }) }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="至少n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56"> 2 </span>
                      <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                    </I18nT>
                  </template>
                </IpSelector>
              </DbFormItem>
              <BkFormItem
                v-if="state.formdata.details.nodes.proxy.length > 0"
                label="">
                <div class="apply-instance-inline">
                  <BkFormItem
                    :label="t('Proxy端口')"
                    label-width="110"
                    property="details.proxy_port"
                    required>
                    <BkInput
                      v-model="state.formdata.details.proxy_port"
                      :max="65535"
                      :min="1025"
                      style="width: 120px"
                      type="number" />
                    <span class="ml-16">{{ t('从n起', { n: state.formdata.details.proxy_port }) }}</span>
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
                  :os-types="[OSTypes.Linux]"
                  @change="handleMasterIpChange">
                  <template #desc>
                    {{ t('至少1台_且机器数要和Slave相等') }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="至少n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56"> 1 </span>
                      <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
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
                  :os-types="[OSTypes.Linux]"
                  @change="handleSlaveIpChange">
                  <template #desc>
                    {{ t('至少1台_且机器数要和Master相等') }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="至少n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56"> 1 </span>
                      <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                    </I18nT>
                  </template>
                </IpSelector>
              </DbFormItem>
              <!-- 保留了资源池逻辑，后续确认不需要可以去掉 -->
              <BkFormItem
                :label="isManualInput ? t('总容量') : t('申请容量')"
                property="details.cap_key"
                required>
                <div
                  :key="capSpecsKey"
                  v-bk-tooltips="{
                    disabled: !disableCapSpecs,
                    content: t('请确保Master和Slave的机器数量至少1台且机器数要相等'),
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
                  {{ t('单实例容量x分片数_根据选择的主机自动计算所有的组合') }}
                </p>
              </BkFormItem>
            </div>
            <div
              v-else
              class="mb-24">
              <BkFormItem
                :label="t('Proxy规格')"
                required>
                <div class="resource-pool-item">
                  <BkFormItem
                    :label="t('规格')"
                    property="details.resource_spec.proxy.spec_id"
                    required>
                    <SpecSelector
                      ref="specProxyRef"
                      v-model="state.formdata.details.resource_spec.proxy.spec_id"
                      :biz-id="state.formdata.bk_biz_id"
                      :city="state.formdata.details.city_code"
                      :cloud-id="state.formdata.details.bk_cloud_id"
                      :cluster-type="DBTypes.REDIS"
                      machine-type="proxy"
                      style="width: 314px" />
                  </BkFormItem>
                  <BkFormItem
                    :label="t('数量')"
                    property="details.resource_spec.proxy.count"
                    required>
                    <BkInput
                      v-model="state.formdata.details.resource_spec.proxy.count"
                      :min="2"
                      type="number" />
                    <span class="input-desc">{{ t('至少n台', { n: 2 }) }}</span>
                  </BkFormItem>
                </div>
              </BkFormItem>
              <BkFormItem
                :label="t('后端存储规格')"
                required>
                <BackendQPSSpec
                  ref="specBackendRef"
                  v-model="state.formdata.details.resource_spec.backend_group"
                  :biz-id="state.formdata.bk_biz_id"
                  :cloud-id="state.formdata.details.bk_cloud_id"
                  :cluster-type="typeInfos.cluster_type"
                  :machine-type="specClusterMachineMap[typeInfos.cluster_type]" />
              </BkFormItem>
              <BkFormItem
                :label="t('访问端口')"
                property="details.proxy_port"
                required>
                <BkInput
                  v-model="state.formdata.details.proxy_port"
                  clearable
                  :max="60000"
                  :min="50000"
                  style="width: 185px"
                  type="number" />
                <span class="input-desc">
                  {{ t('范围min_max', { min: 50000, max: 60000 }) }}
                </span>
              </BkFormItem>
            </div>
          </Transition>
          <BkFormItem :label="t('备注')">
            <BkInput
              v-model="state.formdata.remark"
              :maxlength="100"
              :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
              style="width: 655px"
              type="textarea" />
          </BkFormItem>
        </DbCard>
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="baseState.isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="ml-8 w-88"
        :disabled="baseState.isSubmitting"
        @click="handleResetFormdata">
        {{ t('重置') }}
      </BkButton>
      <BkButton
        class="ml-8 w-88"
        :disabled="baseState.isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </SmartAction>
  <DbSideslider
    v-model:is-show="isShowRecommendArchitectrue"
    class="recommend-architecture-sideslider"
    :show-footer="false"
    :title="t('如何选择架构？')"
    width="1110">
    <RecommendArchitectrue />
  </DbSideslider>
</template>

<script setup lang="ts">
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { RedisFunctions } from '@services/model/function-controller/functionController';
  import { getCapSpecs } from '@services/source/infras';
  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase, useTicketCloneInfo } from '@hooks';

  import { useFunController } from '@stores';

  import { ClusterTypes, DBTypes, MachineTypes, OSTypes, TicketTypes } from '@common/const';
  import { nameRegx } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import AffinityItem from '@views/db-manage/common/apply-items/AffinityItem.vue';
  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import CloudItem from '@views/db-manage/common/apply-items/CloudItem.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import DeployVersion from '@views/db-manage/common/apply-items/DeployVersion.vue';
  import RegionItem from '@views/db-manage/common/apply-items/RegionItem.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import PasswordInput from '@views/db-manage/common/password-input/Index.vue';

  import { generateId } from '@utils';

  import { specClusterMachineMap } from '../common/const';

  import { redisClusterTypes, redisIpSources } from './common/const';
  import BackendQPSSpec from './components/backend-spec/Index.vue';
  import RecommendArchitectrue from './components/recommend-architectrue/Index.vue';

  type CapSepcs = ServiceReturnType<typeof getCapSpecs>[number];

  type Version = {
    value: string;
    label: string;
  };

  // 基础设置
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const { t } = useI18n();
  const funControllerStore = useFunController();
  const route = useRoute();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_CLUSTER_APPLY,
    onSuccess(formdata) {
      state.formdata = formdata;
      bizState.hasEnglishName = !!formdata.details.db_app_abbr;
    },
  });

  const renderRedisClusterTypes = computed(() => {
    const values = Object.values(redisClusterTypes);
    const redisController = funControllerStore.funControllerData.redis;

    return values.filter((item) => redisController.children[item.id as RedisFunctions]?.is_enabled);
  });

  /** 初始化数据 */
  const initData = () => ({
    bk_biz_id: '' as number | '',
    ticket_type: TicketTypes.REDIS_CLUSTER_APPLY,
    remark: '',
    details: {
      bk_cloud_id: 0,
      db_app_abbr: '',
      proxy_port: 50000,
      cluster_name: '',
      cluster_alias: '',
      cluster_type: renderRedisClusterTypes.value[0].id,
      city_code: '',
      db_version: '',
      cap_key: '',
      ip_source: redisIpSources.resource_pool.id,
      disaster_tolerance_level: 'NONE',
      proxy_pwd: '',
      nodes: {
        proxy: [] as HostInfo[],
        master: [] as HostInfo[],
        slave: [] as HostInfo[],
      },
      resource_spec: {
        proxy: {
          spec_id: '' as number | '',
          count: 2,
        },
        backend_group: {
          count: 1,
          spec_id: '' as number | '',
          capacity: '' as number | string,
          future_capacity: '' as number | string,
          affinity: 'NONE',
          location_spec: {
            city: '',
            sub_zone_ids: [] as number[],
          },
        },
      },
    },
  });

  const formRef = ref();
  const masterRef = ref();
  const slaveRef = ref();
  const specProxyRef = ref();
  const specBackendRef = ref();
  const regionItemRef = ref();
  const passwordRef = ref<InstanceType<typeof PasswordInput>>();
  const capSpecsKey = ref(generateId('CLUSTER_APPLAY_CAP_'));
  const isShowRecommendArchitectrue = ref(false);
  const cloudInfo = ref({
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
    'details.cluster_name': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (val: string) => nameRegx.test(val),
      },
    ],
    'details.nodes.proxy': [
      {
        message: t('Proxy数量至少为2台'),
        trigger: 'change',
        validator: (value: HostInfo[]) => value.length >= 2,
      },
    ],
    'details.nodes.master': [
      {
        message: t('Master数量至少为1台_且机器数要和Slave相等'),
        trigger: 'change',
        validator: (value: HostInfo[]) =>
          value.length > 0 && state.formdata.details.nodes.slave.length === value.length,
      },
    ],
    'details.nodes.slave': [
      {
        message: t('Slave数量至少为1台_且机器数要和Master相等'),
        trigger: 'change',
        validator: (value: HostInfo[]) =>
          value.length > 0 && state.formdata.details.nodes.master.length === value.length,
      },
    ],
    'details.proxy_pwd': [
      {
        trigger: 'blur',
        message: t('密码不能为空'),
        validator: (value: string) => !!value,
      },
      {
        trigger: 'blur',
        message: t('密码不满足要求'),
        validator: () => passwordRef.value!.validate(),
      },
    ],
  };

  const isManualInput = computed(() => state.formdata.details.ip_source === redisIpSources.manual_input.id);

  const disableCapSpecs = computed(() => {
    const { master, slave } = state.formdata.details.nodes;
    // 资源池模式不需要判断
    if (!isManualInput.value) {
      return false;
    }
    return master.length === 0 || master.length !== slave.length;
  });

  const typeInfos = computed(() => {
    const types = {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        cluster_type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        machine_type: MachineTypes.REDIS_TENDIS_CACHE,
        backend_machine_type: 'tendiscache',
        pkg_type: 'redis',
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        cluster_type: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        machine_type: MachineTypes.REDIS_TENDIS_SSD,
        backend_machine_type: 'tendisssd',
        pkg_type: 'tendisssd',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        cluster_type: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        machine_type: MachineTypes.REDIS_TENDIS_PLUS,
        backend_machine_type: 'tendisplus',
        pkg_type: 'tendisplus',
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        cluster_type: ClusterTypes.PREDIXY_REDIS_CLUSTER,
        machine_type: MachineTypes.REDIS_TENDIS_CACHE,
        backend_machine_type: 'tendiscache',
        pkg_type: 'redis',
      },
    };
    return types[state.formdata.details.cluster_type as keyof typeof types];
  });
  // const isDefaultCity = computed(() => state.formdata.details.city_code === 'default');

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getDispalyCapSpecs = (item: CapSepcs) => {
    if (state.formdata.details.cluster_type === ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE) {
      return `${item.total_disk}(${item.max_disk} GB x ${item.shard_num}${t('分片')})`;
    }
    return `${item.total_memory}(${getMaxMemoryToGb(item.maxmemory)} x ${item.shard_num}${t('分片')})`;
  };

  /**
   * 单实例容量转为 GB
   */
  const getMaxMemoryToGb = (mem: number) => `${(mem / 1024).toFixed(1)} GB`;

  /**
   * 获取 redis 容量信息
   */
  const fetchCapSpecs = (cityCode: string) => {
    state.formdata.details.cap_key = '';
    const { master, slave } = state.formdata.details.nodes;
    if (isManualInput.value && (master.length === 0 || master.length !== slave.length)) {
      return;
    }
    state.isLoadCapSpecs = true;
    getCapSpecs({
      cityCode,
      cluster_type: state.formdata.details.cluster_type,
      ip_source: state.formdata.details.ip_source,
      nodes: {
        master: formatNodes(master),
        slave: formatNodes(slave),
      },
    })
      .then((res) => {
        state.capSpecs = res;
        const suggestItem = res.find((item) => item.selected);
        if (suggestItem) {
          state.formdata.details.cap_key = suggestItem.cap_key;
        } else if (res.length > 0) {
          state.formdata.details.cap_key = res[0].cap_key;
        }
      })
      .finally(() => {
        state.isLoadCapSpecs = false;
      });
  };

  const handleChangeClusterType = () => {
    const count = [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER, ClusterTypes.PREDIXY_REDIS_CLUSTER].includes(
      state.formdata.details.cluster_type,
    )
      ? 3
      : 1;
    state.formdata.details.db_version = '';
    state.formdata.details.resource_spec.proxy.spec_id = '';
    state.formdata.details.resource_spec.backend_group = {
      ...state.formdata.details.resource_spec.backend_group,
      count,
      spec_id: '',
      capacity: '',
      future_capacity: '',
    };
    isManualInput.value && fetchCapSpecs('');
  };

  /**
   * 变更业务
   */
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    // 清空 ip 选择器
    state.formdata.details.nodes.proxy = [];
    state.formdata.details.nodes.master = [];
    state.formdata.details.nodes.slave = [];
  };

  /**
   * 变更所属管控区域
   */
  const handleChangeCloud = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;

    // 清空 ip 选择器
    state.formdata.details.nodes.proxy = [];
    state.formdata.details.nodes.master = [];
    state.formdata.details.nodes.slave = [];
  };

  /** 重置表单 */
  const handleResetFormdata = () => {
    InfoBox({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      cancelText: t('取消'),
      onConfirm: () => {
        state.formdata = initData();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };

  const ipSelectorDisableSubmitMethods = {
    proxy: (hostList: Array<any>) => (hostList.length >= 2 ? false : t('至少n台', { n: 2 })),
    master: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
    slave: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
  };

  const makeMapByHostId = (hostList: HostInfo[]) =>
    hostList.reduce(
      (result, item) => ({
        ...result,
        [item.host_id]: true,
      }),
      {} as Record<number, boolean>,
    );

  // proxy、master、slave 互斥
  const proxyDisableHostMethod = (data: any) => {
    const masterHostMap = makeMapByHostId(state.formdata.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master使用');
    }
    const slaveHostMap = makeMapByHostId(state.formdata.details.nodes.slave);
    if (slaveHostMap[data.host_id]) {
      return t('主机已被Slave使用');
    }

    return false;
  };

  // proxy、master、slave 互斥
  const masterDisableHostMethod = (data: any) => {
    const proxyHostMap = makeMapByHostId(state.formdata.details.nodes.proxy);
    if (proxyHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }
    const slaveHostMap = makeMapByHostId(state.formdata.details.nodes.slave);
    if (slaveHostMap[data.host_id]) {
      return t('主机已被Slave使用');
    }

    return false;
  };

  // proxy、master、slave 互斥
  const slaveDisableHostMethod = (data: any) => {
    const proxyHostMap = makeMapByHostId(state.formdata.details.nodes.proxy);
    if (proxyHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }
    const masterHostMap = makeMapByHostId(state.formdata.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master使用');
    }

    return false;
  };

  /**
   * 更新 Proxy IP
   */
  const handleProxyIpChange = (data: HostInfo[]) => {
    state.formdata.details.nodes.proxy = [...data];
  };

  /**
   * 更新 Master IP
   */
  const handleMasterIpChange = (data: HostInfo[]) => {
    state.formdata.details.nodes.master = [...data];
    fetchCapSpecs(state.formdata.details.city_code);
    masterRef.value?.validate?.();
    slaveRef.value?.validate?.();
    capSpecsKey.value = generateId('CLUSTER_APPLAY_CAP_');
  };

  /**
   * 更新 Slave IP
   */
  const handleSlaveIpChange = (data: HostInfo[]) => {
    state.formdata.details.nodes.slave = [...data];
    fetchCapSpecs(state.formdata.details.city_code);
    masterRef.value?.validate?.();
    slaveRef.value?.validate?.();
    capSpecsKey.value = generateId('CLUSTER_APPLAY_CAP_');
  };

  /**
   * 格式化 IP 提交格式
   */
  const formatNodes = (hosts: HostInfo[]) =>
    hosts.map((host) => ({
      ip: host.ip,
      bk_host_id: host.host_id,
      bk_cloud_id: host.cloud_id,
      bk_cpu: host.bk_cpu,
      bk_disk: host.bk_disk,
      bk_mem: host.bk_mem,
      bk_biz_id: host.biz.id,
    }));

  const handleRecommendArchitectrueOpen = () => {
    isShowRecommendArchitectrue.value = true;
  };

  const handleSubmit = async () => {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const details: Record<string, any> = _.cloneDeep(state.formdata.details);
      const { cityCode } = regionItemRef.value.getValue();

      const regionAndDisasterParams = {
        affinity: details.resource_spec.backend_group.affinity,
        location_spec: {
          city: cityCode,
          sub_zone_ids: [],
        },
      };

      if (state.formdata.details.ip_source === 'resource_pool') {
        delete details.nodes;
        // 集群容量需求不需要提交
        delete details.resource_spec.backend_group.capacity;
        delete details.resource_spec.backend_group.future_capacity;

        const specInfo = specBackendRef.value.getData();
        return {
          ...details,
          cluster_shard_num: Number(specInfo.cluster_shard_num),
          disaster_tolerance_level: details.resource_spec.backend_group.affinity,
          resource_spec: {
            proxy: {
              ...details.resource_spec.proxy,
              ...specProxyRef.value.getData(),
              ...regionAndDisasterParams,
              count: Number(details.resource_spec.proxy.count),
              spec_cluster_type: typeInfos.value.cluster_type,
              spec_machine_type: typeInfos.value.machine_type,
            },
            backend_group: {
              ...details.resource_spec.backend_group,
              count: specInfo.machine_pair,
              spec_info: specInfo,
              location_spec: {
                city: cityCode,
                sub_zone_ids: [],
              },
            },
          },
        };
      }

      delete details.resource_spec;
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
  };

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.back();
        return;
      }
      router.push({
        name: route.query.from as string,
      });
    },
  });
</script>

<style lang="less" scoped>
  @import '@styles/applyInstance.less';

  .apply-instance {
    :deep(.item-input) {
      width: 435px;
    }

    .apply-instance-inline {
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

    :deep(.password-form-item) {
      width: 435px;
    }

    .resource-pool-item {
      width: 655px;
      padding: 24px 0;
      background-color: #f5f7fa;
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

    .recommend-architectrue-btn {
      font-size: 12px;
    }
  }

  .apply-instance-content {
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

<style lang="less">
  .recommend-architecture-sideslider {
    .bk-modal-content {
      max-height: calc(100vh - 51px);
      overflow-y: auto;
    }
  }
</style>
