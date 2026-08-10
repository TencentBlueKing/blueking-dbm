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
    <div class="redis-cluster-apply mb-16">
      <DbForm
        ref="formRef"
        class="apply-form"
        :label-width="200"
        :model="formData"
        :rules="rules">
        <DbCard :title="t('基本信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="redis_cluster_apply"
            @change-biz="handleChangeBiz" />
          <ClusterName
            v-model="formData.details.cluster_name"
            :biz-id="formData.bk_biz_id"
            :cluster-type="formData.details.cluster_type"
            :db-app-abbr="formData.details.db_app_abbr" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            cluster-type="redis" />
        </DbCard>
        <RegionRequirements
          ref="regionRequirements"
          v-model="formData.details"
          @cloud-change="handleCloudChange" />
        <DbCard :title="t('部署配置')">
          <BkFormItem
            :label="t('部署架构')"
            property="details.cluster_type"
            required>
            <BkRadioGroup
              v-model="formData.details.cluster_type"
              @change="handleChangeClusterType">
              <BkPopover
                v-for="item of renderRedisClusterTypes"
                :key="item.id"
                placement="top"
                :popover-delay="0"
                theme="light"
                trigger="hover">
                <BkRadioButton
                  :label="item.id"
                  style="flex: 0 0 130px">
                  {{ item.text }}
                </BkRadioButton>
                <template #content>
                  <div class="redis-cluster-apply-instance-content">
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
              v-model="formData.details.db_version"
              :db-type="DBTypes.REDIS"
              :query-key="typeInfos.pkg_type" />
          </BkFormItem>
          <BkFormItem
            :label="t('访问端口')"
            property="details.proxy_port"
            required>
            <DbInput
              v-model="formData.details.proxy_port"
              clearable
              :max="60000"
              :min="50000"
              style="width: 185px"
              type="number" />
            <span class="input-desc">
              {{ t('范围min_max', { min: 50000, max: 60000 }) }}
            </span>
          </BkFormItem>
          <BkFormItem
            :label="t('访问密码')"
            property="details.proxy_pwd"
            required>
            <PasswordInput
              ref="passwordRef"
              v-model="formData.details.proxy_pwd"
              :db-type="DBTypes.REDIS"
              @verify-result="verifyResult" />
          </BkFormItem>
          <!-- <BkFormItem
            :label="t('服务器选择')"
            property="details.ip_source"
            required>
            <BkRadioGroup
              v-model="formData.details.ip_source"
              class="item-input"
              @change="fetchCapSpecs(formData.details.city_code)">
              <BkRadioButton
                :key="redisIpSources.resource_pool.id"
                :label="redisIpSources.resource_pool.id">
                {{ redisIpSources.resource_pool.text }}
              </BkRadioButton>
              <BkRadioButton
                v-for="item of Object.values(redisIpSources)"
                :key="item.id"
                :label="item.id">
                {{ item.text }}
              </BkRadioButton>
            </BkRadioGroup>
          </BkFormItem> -->
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
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.proxy"
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
                v-if="formData.details.nodes.proxy.length > 0"
                label="">
                <div class="apply-instance-inline">
                  <BkFormItem
                    :label="t('Proxy端口')"
                    label-width="110"
                    property="details.proxy_port"
                    required>
                    <DbInput
                      v-model="formData.details.proxy_port"
                      :max="65535"
                      :min="1025"
                      style="width: 120px"
                      type="number" />
                    <span class="ml-16">{{ t('从n起', { n: formData.details.proxy_port }) }}</span>
                  </BkFormItem>
                </div>
              </BkFormItem>
              <DbFormItem
                ref="masterRef"
                label="Master"
                property="details.nodes.master"
                required>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.master"
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
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.slave"
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
                    v-model="formData.details.cap_key"
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
                  class="apply-form-tips">
                  {{ t('单实例容量x分片数_根据选择的主机自动计算所有的组合') }}
                </p>
              </BkFormItem>
            </div>
            <div
              v-else
              class="mb-24">
              <BkFormItem label="Proxy">
                <div class="resource-pool-item">
                  <BkFormItem
                    :label="t('规格')"
                    property="details.resource_spec.proxy.spec_id"
                    required>
                    <SpecSelector
                      ref="specProxyRef"
                      v-model="formData.details.resource_spec.proxy.spec_id"
                      :biz-id="formData.bk_biz_id"
                      :city="formData.details.city_code"
                      :cloud-id="formData.details.bk_cloud_id"
                      :cluster-type="DBTypes.REDIS"
                      machine-type="proxy"
                      style="width: 314px"
                      :subzone-ids="formData.details.sub_zone_ids" />
                  </BkFormItem>
                  <ResourcePreview
                    v-model:tag-list="formData.details.resource_spec.proxy.labels"
                    :biz-id="formData.bk_biz_id"
                    :params="{
                      city: formData.details.city_name,
                      subzones: formData.details.sub_zone_names.join('，'),
                      subzone_ids: formData.details.sub_zone_ids.join(','),
                      for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                      resource_types: [DBTypes.REDIS, 'PUBLIC'],
                      spec_id: Number(formData.details.resource_spec.proxy.spec_id),
                      labels: formData.details.resource_spec.proxy.labels.map((item) => item.id).join(','),
                    }"
                    property="details.resource_spec.proxy.labels" />
                  <BkFormItem
                    :label="t('数量')"
                    property="details.resource_spec.proxy.count"
                    required>
                    <DbInput
                      v-model="formData.details.resource_spec.proxy.count"
                      :min="2"
                      type="number" />
                    <span class="input-desc">{{ t('至少n台', { n: 2 }) }}</span>
                  </BkFormItem>
                  <BkFormItem
                    v-if="isLoadBalanceShow"
                    :label="t('负载均衡')"
                    :required="false">
                    <BkCheckbox
                      v-model="formData.details.apply_clb"
                      v-db-console="'common.clb'">
                      CLB
                    </BkCheckbox>
                    <BkCheckbox
                      v-model="formData.details.apply_polaris"
                      v-db-console="'common.polaris'">
                      {{ t('北极星') }}
                    </BkCheckbox>
                  </BkFormItem>
                </div>
              </BkFormItem>
              <BkFormItem :label="t('后端存储')">
                <BackendQPSSpec
                  ref="specBackendRef"
                  v-model="formData.details.resource_spec.backend_group"
                  v-model:apply-schema="applySchema"
                  :biz-id="formData.bk_biz_id"
                  :city-code="formData.details.city_code"
                  :city-name="formData.details.city_name"
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="typeInfos.cluster_type"
                  :machine-type="backendMachineType"
                  :subzone-ids="formData.details.sub_zone_ids"
                  :subzone-names="formData.details.sub_zone_names" />
              </BkFormItem>
            </div>
          </Transition>
        </DbCard>
        <DbCard :title="t('补充信息')">
          <EstimatedCost
            :params="{
              db_type: DBTypes.REDIS,
              resource_spec: resourceSepc,
            }" />
          <NotifyRelatedPersons
            ref="notifyRelatedPersonsRef"
            v-model="formData.send_msg_config"
            :biz-id="formData.bk_biz_id"
            :db-type="DBTypes.REDIS" />
          <BkFormItem :label="t('备注')">
            <DbInput
              v-model="formData.remark"
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
        v-bk-tooltips="{
          content: t('密码不符合要求'),
          disabled: !Boolean(formData.details.proxy_pwd) || passwordIsPass,
        }"
        class="w-88"
        :disabled="!passwordIsPass"
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
  import { inject } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { RedisFunctions } from '@services/model/function-controller/functionController';
  import type { Redis } from '@services/model/ticket/ticket';
  import { getCapSpecs } from '@services/source/infras';
  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { useFunController } from '@stores';

  import { Affinity, ClusterTypes, DBTypes, MachineTypes, MessageTypes, OSTypes, TicketTypes } from '@common/const';
  import { clusterNameSymbolRegx } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import DeployVersion from '@views/db-manage/common/apply-items/DeployVersion.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import NotifyRelatedPersons from '@views/db-manage/common/apply-items/NotifyRelatedPersons.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/Index.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { APPLY_SCHEME } from '@views/db-manage/common/apply-schema/Index.vue';
  import PasswordInput from '@views/db-manage/common/password-input/Index.vue';
  import { QueryKeyMap } from '@views/db-manage/redis/common/const';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import { checkDbConsole, generateId } from '@utils';

  import { specClusterMachineMap } from '../common/const';

  import { redisClusterTypes, redisIpSources } from './common/const';
  import BackendQPSSpec from './components/backend-spec/Index.vue';
  import RecommendArchitectrue from './components/recommend-architectrue/Index.vue';

  type CapSepcs = ServiceReturnType<typeof getCapSpecs>[number];

  type Version = {
    label: string;
    value: string;
  };

  // 基础设置
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);
  const { t } = useI18n();
  const funControllerStore = useFunController();
  const route = useRoute();
  const router = useRouter();

  const isLoadBalanceShow = checkDbConsole('common.clb') || checkDbConsole('common.polaris');

  useTicketDetail<Redis.ClusterApply>(TicketTypes.REDIS_CLUSTER_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
        send_msg_config: {
          ...formData.send_msg_config,
          is_send: ticketDetail.send_msg_config.is_send,
          receiver__username: ticketDetail.send_msg_config.is_send
            ? ticketDetail.send_msg_config.receiver__username
            : [],
        },
      });
      Object.assign(formData.details, {
        apply_clb: details.apply_clb,
        apply_polaris: details.apply_polaris,
        bk_cloud_id: details.bk_cloud_id,
        city_code: details.city_code,
        cluster_alias: details.cluster_alias,
        cluster_name: details.cluster_name,
        cluster_type: details.cluster_type,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        ip_source: details.ip_source,
        proxy_port: details.proxy_port,
      });

      if (details.ip_source === 'resource_pool') {
        const { backend_group: backendGroup, proxy } = details.resource_spec!;
        const backendGroupLabels = (backendGroup.labels || []).map((labelItem, labelIndex) => ({
          id: Number(labelItem),
          value: backendGroup.label_names[labelIndex],
        }));
        const proxyLabels = (proxy.labels || []).map((labelItem, labelIndex) => ({
          id: Number(labelItem),
          value: proxy.label_names[labelIndex],
        }));
        const resourceSpec = {
          backend_group: {
            ...formData.details.resource_spec.backend_group,
            labels: backendGroupLabels,
          },
          proxy: {
            count: proxy.count,
            labels: proxyLabels,
            spec_id: proxy.spec_id,
          },
        };
        const subzoneIds = details.resource_spec!.backend_group.location_spec.sub_zone_ids || [];
        Object.assign(formData.details, {
          resource_spec: resourceSpec,
          sub_zone_ids: subzoneIds,
        });
        nextTick(() => {
          regionRequirementsRef.value!.setInitSubzone(subzoneIds);
        });
      }
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
    details: {
      apply_clb: false,
      apply_polaris: false,
      bk_cloud_id: 0,
      cap_key: '',
      city_code: '',
      city_name: '',
      cluster_alias: '',
      cluster_name: '',
      cluster_type: renderRedisClusterTypes.value[0].id,
      db_app_abbr: '',
      db_version: '',
      disaster_tolerance_level: Affinity.CROS_SUBZONE,
      ip_source: redisIpSources.resource_pool.id,
      nodes: {
        master: [] as HostInfo[],
        proxy: [] as HostInfo[],
        slave: [] as HostInfo[],
      },
      proxy_port: 50000,
      proxy_pwd: '',
      resource_spec: {
        backend_group: {
          affinity: '',
          capacity: '' as number | string,
          count: '' as number | string,
          future_capacity: '' as number | string,
          labels: [] as {
            id: number;
            value: string;
          }[],
          location_spec: {
            city: '',
            sub_zone_ids: [] as number[],
          },
          spec_id: '' as number | '',
        },
        proxy: {
          count: 2,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '' as number | '',
        },
      },
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
    },
    remark: '',
    send_msg_config: {
      is_send: true,
      msg_type: [MessageTypes.MAIL],
      receiver__username: [] as string[],
    },
    ticket_type: TicketTypes.REDIS_CLUSTER_APPLY,
  });

  const regionRequirementsRef = useTemplateRef('regionRequirements');
  const notifyRelatedPersonsRef = useTemplateRef('notifyRelatedPersonsRef');

  const formRef = ref();
  const masterRef = ref();
  const slaveRef = ref();
  const specProxyRef = ref();
  const specBackendRef = ref();
  const passwordRef = ref<InstanceType<typeof PasswordInput>>();
  const capSpecsKey = ref(generateId('CLUSTER_APPLAY_CAP_'));
  const isShowRecommendArchitectrue = ref(false);
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });
  const passwordIsPass = ref(false);
  const applySchema = ref(APPLY_SCHEME.AUTO);

  const formData = reactive(initData());

  const state = reactive({
    capSpecs: [] as CapSepcs[],
    isLoadCapSpecs: false,
    isLoadVersion: false,
    versions: [] as Version[],
  });

  const rules = {
    'details.cluster_name': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (val: string) => clusterNameSymbolRegx.test(val),
      },
    ],
    'details.nodes.master': [
      {
        message: t('Master数量至少为1台_且机器数要和Slave相等'),
        trigger: 'change',
        validator: (value: HostInfo[]) => value.length > 0 && formData.details.nodes.slave.length === value.length,
      },
    ],
    'details.nodes.proxy': [
      {
        message: t('Proxy数量至少为2台'),
        trigger: 'change',
        validator: (value: HostInfo[]) => value.length >= 2,
      },
    ],
    'details.nodes.slave': [
      {
        message: t('Slave数量至少为1台_且机器数要和Master相等'),
        trigger: 'change',
        validator: (value: HostInfo[]) => value.length > 0 && formData.details.nodes.master.length === value.length,
      },
    ],
    'details.proxy_pwd': [
      {
        message: t('密码不能为空'),
        trigger: 'blur',
        validator: (value: string) => !!value,
      },
      {
        message: t('密码不满足要求'),
        trigger: 'blur',
        validator: () => passwordRef.value!.validate(),
      },
    ],
  };

  const isManualInput = computed(() => formData.details.ip_source === redisIpSources.manual_input.id);

  const disableCapSpecs = computed(() => {
    const { master, slave } = formData.details.nodes;
    // 资源池模式不需要判断
    if (!isManualInput.value) {
      return false;
    }
    return master.length === 0 || master.length !== slave.length;
  });

  const typeInfos = computed(() => {
    const types = {
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        backend_machine_type: 'tendiscache',
        cluster_type: ClusterTypes.PREDIXY_REDIS_CLUSTER,
        machine_type: MachineTypes.REDIS_TENDIS_CACHE,
        pkg_type: QueryKeyMap[ClusterTypes.PREDIXY_REDIS_CLUSTER],
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        backend_machine_type: 'tendisplus',
        cluster_type: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        machine_type: MachineTypes.REDIS_TENDIS_PLUS,
        pkg_type: QueryKeyMap[ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER],
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE]: {
        backend_machine_type: 'tendisplus',
        cluster_type: ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE,
        machine_type: MachineTypes.REDIS_TENDIS_PLUS,
        pkg_type: QueryKeyMap[ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE],
      },
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        backend_machine_type: 'tendiscache',
        cluster_type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        machine_type: MachineTypes.REDIS_TENDIS_CACHE,
        pkg_type: QueryKeyMap[ClusterTypes.TWEMPROXY_REDIS_INSTANCE],
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        backend_machine_type: 'tendisssd',
        cluster_type: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        machine_type: MachineTypes.REDIS_TENDIS_SSD,
        pkg_type: QueryKeyMap[ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE],
      },
    };
    return types[formData.details.cluster_type as keyof typeof types];
  });

  const backendMachineType = computed(() =>
    typeInfos.value.cluster_type === ClusterTypes.PREDIXY_REDIS_CLUSTER && applySchema.value === APPLY_SCHEME.AUTO
      ? ClusterTypes.PREDIXY_REDIS_CLUSTER
      : specClusterMachineMap[typeInfos.value.cluster_type],
  );

  const resourceSepc = computed(() => {
    const specInfo = specBackendRef.value?.getData();
    return {
      backend_group: {
        count: Number(specInfo?.machine_pair || 0),
        spec_id: formData.details.resource_spec.backend_group.spec_id,
      },
      proxy: {
        count: Number(formData.details.resource_spec.proxy.count || 0),
        spec_id: formData.details.resource_spec.proxy.spec_id,
      },
    } as ComponentProps<typeof EstimatedCost>['params']['resource_spec'];
  });

  const verifyResult = (isPass: boolean) => {
    passwordIsPass.value = isPass;
  };

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getDispalyCapSpecs = (item: CapSepcs) => {
    if (formData.details.cluster_type === ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE) {
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
    formData.details.cap_key = '';
    const { master, slave } = formData.details.nodes;
    if (isManualInput.value && (master.length === 0 || master.length !== slave.length)) {
      return;
    }
    state.isLoadCapSpecs = true;
    getCapSpecs({
      cityCode,
      cluster_type: formData.details.cluster_type,
      ip_source: formData.details.ip_source,
      nodes: {
        master: formatNodes(master),
        slave: formatNodes(slave),
      },
    })
      .then((res) => {
        state.capSpecs = res;
        const suggestItem = res.find((item) => item.selected);
        if (suggestItem) {
          formData.details.cap_key = suggestItem.cap_key;
        } else if (res.length > 0) {
          formData.details.cap_key = res[0].cap_key;
        }
      })
      .finally(() => {
        state.isLoadCapSpecs = false;
      });
  };

  const handleChangeClusterType = () => {
    // const count = [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER].includes(
    //   formData.details.cluster_type,
    // )
    //   ? 3
    //   : 1;
    formData.details.db_version = '';
    formData.details.resource_spec.proxy.spec_id = '';
    formData.details.resource_spec.backend_group = {
      ...formData.details.resource_spec.backend_group,
      capacity: '',
      count: '',
      future_capacity: '',
      spec_id: '',
    };
    if (isManualInput.value) {
      fetchCapSpecs('');
    }
  };

  /**
   * 变更业务
   */
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    // 清空 ip 选择器
    formData.details.nodes.proxy = [];
    formData.details.nodes.master = [];
    formData.details.nodes.slave = [];
    serviceApply?.changeBizId(info.bk_biz_id);
  };

  /**
   * 变更所属管控区域
   */
  const handleCloudChange = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;

    // 清空 ip 选择器
    formData.details.nodes.proxy = [];
    formData.details.nodes.master = [];
    formData.details.nodes.slave = [];
  };

  /** 重置表单 */
  const handleResetFormdata = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, initData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
    });
  };

  const ipSelectorDisableSubmitMethods = {
    master: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
    proxy: (hostList: Array<any>) => (hostList.length >= 2 ? false : t('至少n台', { n: 2 })),
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
    const masterHostMap = makeMapByHostId(formData.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master使用');
    }
    const slaveHostMap = makeMapByHostId(formData.details.nodes.slave);
    if (slaveHostMap[data.host_id]) {
      return t('主机已被Slave使用');
    }

    return false;
  };

  // proxy、master、slave 互斥
  const masterDisableHostMethod = (data: any) => {
    const proxyHostMap = makeMapByHostId(formData.details.nodes.proxy);
    if (proxyHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }
    const slaveHostMap = makeMapByHostId(formData.details.nodes.slave);
    if (slaveHostMap[data.host_id]) {
      return t('主机已被Slave使用');
    }

    return false;
  };

  // proxy、master、slave 互斥
  const slaveDisableHostMethod = (data: any) => {
    const proxyHostMap = makeMapByHostId(formData.details.nodes.proxy);
    if (proxyHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }
    const masterHostMap = makeMapByHostId(formData.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master使用');
    }

    return false;
  };

  /**
   * 更新 Proxy IP
   */
  const handleProxyIpChange = (data: HostInfo[]) => {
    formData.details.nodes.proxy = [...data];
  };

  /**
   * 更新 Master IP
   */
  const handleMasterIpChange = (data: HostInfo[]) => {
    formData.details.nodes.master = [...data];
    fetchCapSpecs(formData.details.city_code);
    masterRef.value?.validate?.();
    slaveRef.value?.validate?.();
    capSpecsKey.value = generateId('CLUSTER_APPLAY_CAP_');
  };

  /**
   * 更新 Slave IP
   */
  const handleSlaveIpChange = (data: HostInfo[]) => {
    formData.details.nodes.slave = [...data];
    fetchCapSpecs(formData.details.city_code);
    masterRef.value?.validate?.();
    slaveRef.value?.validate?.();
    capSpecsKey.value = generateId('CLUSTER_APPLAY_CAP_');
  };

  /**
   * 格式化 IP 提交格式
   */
  const formatNodes = (hosts: HostInfo[]) =>
    hosts.map((host) => ({
      bk_biz_id: host.biz.id,
      bk_cloud_id: host.cloud_id,
      bk_cpu: host.bk_cpu,
      bk_disk: host.bk_disk,
      bk_host_id: host.host_id,
      bk_mem: host.bk_mem,
      ip: host.ip,
    }));

  const handleRecommendArchitectrueOpen = () => {
    isShowRecommendArchitectrue.value = true;
  };

  const handleSubmit = async () => {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const details: Record<string, any> = _.cloneDeep(formData.details);
      const regionAndDisasterParams = regionRequirementsRef.value!.getValue();

      if (formData.details.ip_source === 'resource_pool') {
        delete details.nodes;
        // 集群容量需求不需要提交
        delete details.resource_spec.backend_group.capacity;
        delete details.resource_spec.backend_group.future_capacity;

        const specBackendInfo = specBackendRef.value.getData();
        return {
          ...details,
          cluster_shard_num: Number(specBackendInfo.cluster_shard_num),
          // disaster_tolerance_level: affinity,
          resource_spec: {
            backend_group: {
              ...details.resource_spec.backend_group,
              ...regionAndDisasterParams,
              count: Number(specBackendInfo.machine_pair),
              label_names: details.resource_spec.backend_group.labels.map((item: { value: string }) => item.value),
              labels: details.resource_spec.backend_group.labels.map((item: { id: number }) => String(item.id)),
              spec_info: specBackendInfo,
            },
            proxy: {
              ...details.resource_spec.proxy,
              ...specProxyRef.value.getData(),
              ...regionAndDisasterParams,
              count: Number(details.resource_spec.proxy.count),
              label_names: details.resource_spec.proxy.labels.map((item: { value: string }) => item.value),
              labels: details.resource_spec.proxy.labels.map((item: { id: number }) => String(item.id)),
              spec_cluster_type: typeInfos.value.cluster_type,
              spec_machine_type: typeInfos.value.machine_type,
            },
          },
        };
      }

      delete details.resource_spec;
      return {
        ...details,
        // disaster_tolerance_level: affinity,
        nodes: {
          master: formatNodes(formData.details.nodes.master),
          proxy: formatNodes(formData.details.nodes.proxy),
          slave: formatNodes(formData.details.nodes.slave),
        },
      };
    };
    const params = {
      ...formData,
      details: getDetails(),
      send_msg_config: notifyRelatedPersonsRef.value!.getValue(),
    };

    // 若业务没有英文名称则先创建业务英文名称再创建单据，反正直接创建单据
    if (bizState.hasEnglishName) {
      handleCreateTicket(params);
    } else {
      handleCreateAppAbbr(params);
    }
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

<style lang="less">
  @import '@styles/applyInstance.less';

  .redis-cluster-apply {
    .item-input {
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

    .password-form-item {
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
          .dbm-input {
            width: 314px !important;
          }
        }
      }
    }

    .recommend-architectrue-btn {
      font-size: 12px;
    }
  }

  .redis-cluster-apply-instance-content {
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
