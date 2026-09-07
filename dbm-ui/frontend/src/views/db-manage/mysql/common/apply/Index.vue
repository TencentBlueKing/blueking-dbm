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
        auto-label-width
        class="apply-form"
        :model="formData"
        :rules="rules">
        <DbCard :title="t('基本信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="mysql_apply"
            @change-biz="handleChangeBiz" />
          <ModuleItem
            v-model="formData.details.db_module_id"
            v-model:module-alias-name="moduleAliasName"
            v-model:module-level-config="moduleLevelConfig"
            :biz-id="formData.bk_biz_id"
            :cluster-type="clusterType" />
        </DbCard>
        <RegionRequirements
          ref="regionRequirements"
          v-model="formData.details"
          :type="isSingleType ? 'single' : 'common'"
          @cloud-change="handleCloudChange" />
        <DbCard :title="t('数据库部署信息')">
          <BkFormItem
            v-if="!isSingleType"
            :label="t('Proxy起始端口')"
            property="details.start_proxy_port"
            required>
            <DbInput
              v-model="formData.details.start_proxy_port"
              class="inline-box"
              :max="65535"
              :min="1025"
              type="number" />
            <span class="apply-form-tips ml-10">{{ t('多集群部署时_系统将从起始端口开始自动分配') }}</span>
          </BkFormItem>
          <BkFormItem
            :label="t('MySQL起始端口')"
            property="details.start_mysql_port"
            required>
            <DbInput
              v-model="formData.details.start_mysql_port"
              class="inline-box"
              :max="65535"
              :min="1025"
              type="number" />
            <span
              v-if="isSingleType"
              class="apply-form-tips ml-10">
              {{ t('多实例部署时_系统将从起始端口开始自动分配') }}
            </span>
            <span
              v-else
              class="apply-form-tips ml-10">
              {{ t('多集群部署时_系统将从起始端口开始自动分配') }}
            </span>
          </BkFormItem>
        </DbCard>
        <DbCard :title="t('需求信息')">
          <BkFormItem
            :label="formItemLabels.clusterCount"
            property="details.cluster_count"
            required>
            <DbInput
              v-model="formData.details.cluster_count"
              class="inline-box"
              :min="1"
              :placeholder="t('请输入')"
              type="number"
              @blur="handleCalcIps"
              @change="handleChangeClusterCount" />
          </BkFormItem>
          <BkFormItem
            :label="formItemLabels.instNums"
            property="details.inst_num"
            required>
            <DbInput
              v-model="formData.details.inst_num"
              class="inline-box"
              :max="formData.details.cluster_count"
              :min="1"
              type="number"
              @blur="handleCalcIps" />
          </BkFormItem>
          <BkFormItem
            class="service"
            :label="t('域名设置')"
            required>
            <DomainTable
              v-model:domains="formData.details.domains"
              :formdata="formData"
              :module-alias-name="moduleAliasName"
              :ticket-type="ticketType" />
          </BkFormItem>
          <!-- <BkFormItem
            :label="t('服务器选择')"
            property="details.ip_source"
            required>
            <BkRadioGroup v-model="formData.details.ip_source">
              <BkRadioButton label="resource_pool">
                {{ t('自动从资源池匹配') }}
              </BkRadioButton>
              <BkRadioButton label="manual_input">
                {{ t('业务空闲机') }}
              </BkRadioButton>
            </BkRadioGroup>
          </BkFormItem> -->
          <Transition
            mode="out-in"
            name="dbm-fade">
            <div
              v-if="formData.details.ip_source === 'manual_input'"
              class="mb-24">
              <DbFormItem
                v-if="!isSingleType"
                ref="proxyRef"
                label="Proxy"
                property="details.nodes.proxy"
                required>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.proxy"
                  :disable-dialog-submit-method="disableHostSubmitMethods.proxy"
                  :disable-host-method="proxyDisableHostMethod"
                  :os-types="[OSTypes.Linux]"
                  @change="handleProxyIpChange">
                  <template #desc>
                    {{ t('需n台', { n: hostNums }) }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="需n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56"> {{ hostNums }} </span>
                      <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
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
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.backend"
                  :disable-dialog-submit-method="disableHostSubmitMethods.backend"
                  :disable-host-method="backendDisableHostMethod"
                  :os-types="[OSTypes.Linux]"
                  @change="handleBackendIpChange">
                  <template #desc>
                    {{ t('需n台', { n: hostNums }) }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="需n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56"> {{ hostNums }} </span>
                      <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
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
                :label="t('后端存储资源规格')"
                required>
                <div class="resource-pool-item">
                  <BkFormItem
                    :label="t('规格')"
                    property="details.resource_spec.single.spec_id"
                    required>
                    <SpecSelector
                      ref="specSingleRef"
                      v-model="formData.details.resource_spec.single.spec_id"
                      :biz-id="formData.bk_biz_id"
                      :city="formData.details.city_code"
                      :cloud-id="formData.details.bk_cloud_id"
                      cluster-type="mysql"
                      machine-type="backend"
                      :subzone-ids="formData.details.sub_zone_ids" />
                  </BkFormItem>
                  <ResourcePreview
                    v-model:tag-list="formData.details.resource_spec.single.labels"
                    :biz-id="formData.bk_biz_id"
                    :params="{
                      city: formData.details.city_name,
                      subzones: formData.details.sub_zone_names.join('，'),
                      subzone_ids: formData.details.sub_zone_ids.join(','),
                      for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                      resource_types: [DBTypes.MYSQL, 'PUBLIC'],
                      spec_id: Number(formData.details.resource_spec.single.spec_id),
                      labels: formData.details.resource_spec.single.labels.map((item) => item.id).join(','),
                    }"
                    property="details.resource_spec.single.labels" />
                </div>
              </BkFormItem>
              <template v-else>
                <BkFormItem
                  :label="t('Proxy 存储资源规格')"
                  required>
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
                        cluster-type="mysql"
                        machine-type="proxy"
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
                        resource_types: [DBTypes.MYSQL, 'PUBLIC'],
                        spec_id: Number(formData.details.resource_spec.proxy.spec_id),
                        labels: formData.details.resource_spec.proxy.labels.map((item) => item.id).join(','),
                      }"
                      property="details.resource_spec.proxy.labels" />
                  </div>
                </BkFormItem>
                <BkFormItem
                  :label="t('后端存储资源规格')"
                  required>
                  <div class="resource-pool-item">
                    <BkFormItem
                      :label="t('规格')"
                      property="details.resource_spec.backend.spec_id"
                      required>
                      <SpecSelector
                        ref="specBackendRef"
                        v-model="formData.details.resource_spec.backend.spec_id"
                        :biz-id="formData.bk_biz_id"
                        :city="formData.details.city_code"
                        :cloud-id="formData.details.bk_cloud_id"
                        cluster-type="mysql"
                        machine-type="backend"
                        :subzone-ids="formData.details.sub_zone_ids" />
                    </BkFormItem>
                    <ResourcePreview
                      v-model:tag-list="formData.details.resource_spec.backend.labels"
                      :biz-id="formData.bk_biz_id"
                      :params="{
                        city: formData.details.city_name,
                        subzones: formData.details.sub_zone_names.join('，'),
                        subzone_ids: formData.details.sub_zone_ids.join(','),
                        for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                        resource_types: [DBTypes.MYSQL, 'PUBLIC'],
                        spec_id: Number(formData.details.resource_spec.backend.spec_id),
                        labels: formData.details.resource_spec.backend.labels.map((item) => item.id).join(','),
                      }"
                      property="details.resource_spec.backend.labels" />
                  </div>
                </BkFormItem>
              </template>
            </div>
          </Transition>
          <EstimatedCost
            :params="{
              db_type: DBTypes.MYSQL,
              resource_spec: resourceSepc,
            }" />
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
      <div>
        <BkButton
          class="w-88"
          :loading="baseState.isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="handleShowPreview">
          {{ t('预览') }}
        </BkButton>
        <DbResetButton
          class="ml-8"
          :confirm-handler="handleResetFormdata"
          :disabled="baseState.isSubmitting" />
        <BkButton
          class="ml-8 w-88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
  <!-- 预览功能 -->
  <BkDialog
    v-model:is-show="isShowPreview"
    header-align="left"
    :width="1180">
    <template #header>
      {{ t('实例预览') }}
      <span class="apply-dialog-quantity">{{ t('共n条', { n: formData.details.cluster_count }) }}</span>
    </template>
    <PreviewTable
      :data="previewData"
      :is-show-nodes="formData.details.ip_source === 'manual_input'"
      :is-single-type="isSingleType"
      :nodes="previewNodes" />
    <template #footer>
      <BkButton @click="() => (isShowPreview = false)">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import type { Mysql } from '@services/model/ticket/ticket';
  import { getInfrasHostSpecs } from '@services/source/infras';
  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { Affinity, clusterTypeInfos, ClusterTypes, DBTypes, OSTypes, TicketTypes } from '@common/const';
  import { clusterNameSymbolRegx } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import ModuleItem from '@views/db-manage/common/apply-items/ModuleItem.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/Index.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { getDomainStrategy } from '@views/db-manage/utils/getDomainPreview.ts';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import DomainTable from './components/MySQLDomainTable.vue';
  import PreviewTable from './components/PreviewTable.vue';

  const route = useRoute();
  const { t } = useI18n();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const ticketType = route.name as string;
  const isSingleType = ticketType === TicketTypes.MYSQL_SINGLE_APPLY;
  const clusterType = isSingleType ? ClusterTypes.TENDBSINGLE : ClusterTypes.TENDBHA;

  const getFormData = () => ({
    bk_biz_id: '' as '' | number,
    details: {
      bk_cloud_id: 0,
      charset: '',
      city_code: '',
      city_name: '',
      cluster_count: 1,
      db_app_abbr: '',
      db_module_id: null as null | number,
      disaster_tolerance_level: ticketType === TicketTypes.MYSQL_SINGLE_APPLY ? Affinity.NONE : Affinity.CROS_SUBZONE, // 同 affinity
      domains: [{ key: '' }],
      inst_num: 1,
      ip_source: 'resource_pool',
      nodes: {
        backend: [] as HostInfo[],
        proxy: [] as HostInfo[],
      },
      resource_spec: {
        backend: {
          affinity: '',
          count: 0,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '' as string | number,
        },
        proxy: {
          count: 0,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '' as string | number,
        },
        single: {
          count: 0,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '' as string | number,
        },
      },
      spec: '',
      start_mysql_port: 20000,
      start_proxy_port: 10000,
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
    },
    remark: '',
    ticket_type: ticketType,
  });

  // 基础设置
  const { applyBizInfo, baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();

  useTicketDetail<Mysql.SingleApply>(TicketTypes.MYSQL_SINGLE_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
      });
      Object.assign(formData.details, {
        bk_cloud_id: details.bk_cloud_id,
        city_code: details.city_code,
        cluster_count: details.domains.length,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        domains: details.domains,
        ip_source: details.ip_source,
        start_mysql_port: details.start_mysql_port,
      });

      if (details.ip_source === 'resource_pool') {
        const { backend } = details.resource_spec!;
        const subzoneIds = backend.location_spec.sub_zone_ids || [];
        const labels = (backend.labels || []).map((labelItem, labelIndex) => ({
          id: Number(labelItem),
          value: backend.label_names[labelIndex],
        }));
        const resourceSpec = {
          single: {
            count: backend.count,
            labels,
            spec_id: backend.spec_id,
          },
        };
        Object.assign(formData.details, {
          inst_num: details.domains.length / backend.count,
          resource_spec: resourceSpec,
          sub_zone_ids: subzoneIds,
        });
        nextTick(() => {
          regionRequirementsRef.value!.setInitSubzone(subzoneIds);
        });
      }

      nextTick(() => {
        Object.assign(formData.details, {
          db_module_id: details.db_module_id,
        });
      });
    },
  });

  useTicketDetail<Mysql.HaApply>(TicketTypes.MYSQL_HA_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
      });
      Object.assign(formData.details, {
        bk_cloud_id: details.bk_cloud_id,
        city_code: details.city_code,
        cluster_count: details.domains.length,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        domains: details.domains,
        ip_source: details.ip_source,
        start_mysql_port: details.start_mysql_port,
        start_proxy_port: details.start_proxy_port,
      });

      if (details.ip_source === 'resource_pool') {
        const backendGroup = details.resource_spec.backend_group!;
        const proxy = details.resource_spec.proxy!;
        const subzoneIds = backendGroup.location_spec.sub_zone_ids || [];
        const backendLabels = (backendGroup.labels || []).map((labelItem, labelIndex) => ({
          id: Number(labelItem),
          value: backendGroup.label_names[labelIndex],
        }));
        const proxyLabels = (proxy.labels || []).map((labelItem, labelIndex) => ({
          id: Number(labelItem),
          value: proxy.label_names[labelIndex],
        }));
        const resourceSpec = {
          backend: {
            count: backendGroup.count,
            labels: backendLabels,
            spec_id: backendGroup.spec_id,
          },
          proxy: {
            count: proxy.count,
            labels: proxyLabels,
            spec_id: proxy.spec_id,
          },
        };
        Object.assign(formData.details, {
          inst_num: details.domains.length / backendGroup.count,
          resource_spec: resourceSpec,
          sub_zone_ids: subzoneIds,
        });
        nextTick(() => {
          regionRequirementsRef.value!.setInitSubzone(subzoneIds);
        });
      }

      nextTick(() => {
        Object.assign(formData.details, {
          db_module_id: details.db_module_id,
        });
      });
    },
  });

  const serviceApply = inject(serviceApplyKey);

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const specProxyRef = ref();
  const specBackendRef = ref();
  const specSingleRef = ref();
  const backendRef = ref();
  const proxyRef = ref();
  const moduleRef = ref();
  const moduleAliasName = ref('');
  const moduleLevelConfig = ref({
    charset: '',
    dbVersion: '',
    systemVersionList: [] as string[],
  });

  const hostSpecs = shallowRef<ServiceReturnType<typeof getInfrasHostSpecs>>([]);
  const formData = reactive(getFormData());
  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const rules = computed(() => ({
    'details.db_app_abbr': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (val: string) => clusterNameSymbolRegx.test(val),
      },
    ],
    'details.nodes.backend': [
      {
        message: t('请添加服务器'),
        trigger: 'change',
        validator: () => {
          const counts = formData.details.nodes.backend.length;
          return counts !== 0;
        },
      },
    ],
    'details.nodes.proxy': [
      {
        message: t('请添加服务器'),
        trigger: 'change',
        validator: () => {
          const counts = formData.details.nodes.proxy.length;
          return counts !== 0;
        },
      },
    ],
  }));
  const formItemLabels = computed(() => {
    const labels = {
      backend: 'Master / Slave',
      clusterCount: t('集群数量'),
      instNums: t('每组主机部署集群数量'),
    };
    if (isSingleType) {
      labels.clusterCount = t('实例数量');
      labels.backend = t('服务器');
      labels.instNums = t('每台主机部署实例数量');
    }
    return labels;
  });
  const hostSpecInfo = computed(() => hostSpecs.value.find((info) => info.spec === formData.details.spec));
  const tableData = computed(() => {
    if (moduleAliasName.value && formData.details.db_app_abbr) {
      return formData.details.domains;
    }
    return [];
  });
  const hostNums = computed(() => {
    const { cluster_count: clusterCount, inst_num: instCount } = formData.details;

    if (clusterCount <= 0 || instCount <= 0) {
      return 0;
    }
    const nums = Math.ceil(clusterCount / instCount);
    return isSingleType ? nums : nums * 2;
  });

  const resourceSepc = computed(() => {
    if (isSingleType) {
      return {
        backend: {
          count: hostNums.value,
          spec_id: formData.details.resource_spec.single.spec_id,
        },
      } as ComponentProps<typeof EstimatedCost>['params']['resource_spec'];
    }
    return {
      backend_group: {
        count: Math.floor(hostNums.value / 2),
        spec_id: formData.details.resource_spec.backend.spec_id,
      },
      proxy: {
        count: hostNums.value,
        spec_id: formData.details.resource_spec.proxy.spec_id,
      },
    } as ComponentProps<typeof EstimatedCost>['params']['resource_spec'];
  });

  /**
   * 设置 domain 数量
   */
  watch(
    () => formData.details.cluster_count,
    (count: number) => {
      if (count > 0 && count <= 200) {
        const len = formData.details.domains.length;
        if (count > len) {
          const appends = Array.from({ length: count - len }, () => ({ key: '' }));
          formData.details.domains.push(...appends);
          return;
        }
        if (count < len) {
          formData.details.domains.splice(count - 1, len - count);
          return;
        }
      }
    },
  );

  /**
   * 获取服务器规格列表
   */
  watch(
    () => formData.details.city_code,
    (value: string) => {
      if (value) {
        formData.details.spec = '';
        fetchInfrasHostSpecs();
      }
    },
  );

  const fetchInfrasHostSpecs = () => {
    getInfrasHostSpecs().then((res) => {
      hostSpecs.value = res || [];
    });
  };

  const handleChangeClusterCount = (value: number) => {
    if (value && formData.details.inst_num > value) {
      formData.details.inst_num = value;
    }
  };

  /**
   * 变更业务选择
   */
  const handleChangeBiz = (info: BizItem) => {
    const bizChanged = applyBizInfo(info);
    serviceApply?.changeBizId(info.bk_biz_id);
    if (!bizChanged) {
      return;
    }
    formData.details.db_module_id = null;
    formData.details.nodes.backend = [];
    formData.details.nodes.proxy = [];
    moduleRef.value?.clearValidate();
  };

  /**
   * 变更所属管控区域
   */
  const handleCloudChange = (info: { id: number | string; name: string }) => {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formData.details.nodes.backend = [];
    formData.details.nodes.proxy = [];
  };

  const handleCalcIps = () => {
    nextTick(() => {
      const { backend, proxy } = formData.details.nodes;
      if (hostNums.value < backend.length) {
        formData.details.nodes.backend.splice(hostNums.value);
      }
      if (hostNums.value < proxy.length) {
        formData.details.nodes.proxy.splice(hostNums.value);
      }
    });
  };

  const disableHostSubmitMethods = {
    backend: (hostList: Array<any>) =>
      hostList.length !== hostNums.value
        ? t('xx共需n台', {
            n: hostNums.value,
            title: 'Master / Slave',
          })
        : false,
    proxy: (hostList: Array<any>) =>
      hostList.length !== hostNums.value
        ? t('xx共需n台', {
            n: hostNums.value,
            title: 'Proxy',
          })
        : false,
  };
  const makeMapByHostId = (hostList: HostInfo[]) =>
    hostList.reduce(
      (result, item) => ({
        ...result,
        [item.host_id]: true,
      }),
      {} as Record<number, boolean>,
    );

  // proxy、backend 节点互斥
  const proxyDisableHostMethod = (data: any, list: any[]) => {
    const masterHostMap = makeMapByHostId(formData.details.nodes.backend);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master_Slave使用');
    }

    if (list.length >= hostNums.value && !list.find((item) => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [hostNums.value, list.length]);
    }

    return false;
  };

  const backendDisableHostMethod = (data: any, list: any[]) => {
    const masterHostMap = makeMapByHostId(formData.details.nodes.proxy);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Proxy使用');
    }

    if (list.length >= hostNums.value && !list.find((item) => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [hostNums.value, list.length]);
    }

    return false;
  };

  /**
   * 更新 Proxy IP
   */
  const handleProxyIpChange = (data: HostInfo[]) => {
    formData.details.nodes.proxy = [...data];
    if (formData.details.nodes.proxy.length > 0) {
      proxyRef.value.clearValidate();
    }
  };

  /**
   * 更新 Backend
   */
  const handleBackendIpChange = (data: HostInfo[]) => {
    formData.details.nodes.backend = [...data];
    if (formData.details.nodes.backend.length > 0) {
      backendRef.value.clearValidate();
    }
  };

  /** 获取版本、字符集信息 */
  // watch(
  //   () => fetchState.levelConfigList,
  //   (value) => {
  //     value.forEach((item) => {
  //       Object.keys(leveConfig).forEach((key) => {
  //         if (key === item.conf_name) {
  //           if (item.conf_value !== undefined) {
  //             leveConfig[key as keyof typeof leveConfig] = item.conf_value;
  //           }
  //         }
  //       });
  //     });
  //   },
  // );

  /**
   * 预览功能
   */
  const previewNodes = computed(() => ({
    backend: formatNodes(formData.details.nodes.backend),
    proxy: formatNodes(formData.details.nodes.proxy),
  }));
  const previewData = computed(() => {
    const { charset, dbVersion } = moduleLevelConfig.value;
    return tableData.value.map(({ key }: { key: string }) => {
      const strategy = getDomainStrategy(isSingleType ? ClusterTypes.TENDBSINGLE : ClusterTypes.TENDBHA);
      const domainInfo = strategy(
        {
          clusterName: key,
          dbAppAbbr: formData.details.db_app_abbr,
          moduleName: moduleAliasName.value,
        },
        {
          bizId: formData.bk_biz_id,
        },
      );
      return {
        charset,
        deployStructure: clusterTypeInfos[clusterType].name,
        disasterDefence: t('同城跨园区'),
        domain: `${domainInfo.masterDomain.prefix}${key || '{' + t('集群标识') + '}'}${domainInfo.masterDomain.suffix}`,
        slaveDomain: `${domainInfo.slaveDomain?.prefix}${key || '{' + t('集群标识') + '}'}${domainInfo.slaveDomain?.suffix}`,
        spec: hostSpecInfo.value ? `${hostSpecInfo.value.cpu}/${hostSpecInfo.value.mem}` : '',
        version: dbVersion,
      };
    });
  });
  const isShowPreview = ref(false);
  const handleShowPreview = () => {
    isShowPreview.value = true;
  };

  /**
   * 格式化 IP 提交格式
   */
  const formatNodes = (hosts: HostInfo[]) => {
    return hosts.map((host) => ({
      bk_biz_id: host.biz.id,
      bk_cloud_id: host.cloud_id,
      bk_host_id: host.host_id,
      ip: host.ip,
    }));
  };

  /**
   * 提交申请
   */
  const formRef = ref();
  const handleSubmit = async () => {
    const validate = await formRef.value
      ?.validate()
      .then(() => true)
      .catch(() => false);
    if (validate) {
      baseState.isSubmitting = true;

      const getDetails = () => {
        const details: Record<string, any> = _.cloneDeep(formData.details);
        const regionAndDisasterParams = regionRequirementsRef.value!.getValue();

        if (formData.details.ip_source === 'resource_pool') {
          delete details.nodes;
          if (isSingleType) {
            return {
              ...details,
              resource_spec: {
                backend: {
                  ...details.resource_spec.single,
                  ...specSingleRef.value.getData(),
                  ...regionAndDisasterParams,
                  count: hostNums.value,
                  label_names: details.resource_spec.single.labels.map((item: { value: string }) => item.value),
                  labels: details.resource_spec.single.labels.map((item: { id: number }) => String(item.id)),
                },
              },
            };
          }

          return {
            ...details,
            // disaster_tolerance_level: affinity,
            resource_spec: {
              backend_group: {
                ...details.resource_spec.backend,
                ...specBackendRef.value.getData(),
                ...regionAndDisasterParams,
                count: Math.floor(hostNums.value / 2),
                label_names: details.resource_spec.backend.labels.map((item: { value: string }) => item.value),
                labels: details.resource_spec.backend.labels.map((item: { id: number }) => String(item.id)),
              },
              proxy: {
                ...details.resource_spec.proxy,
                ...specProxyRef.value.getData(),
                ...regionAndDisasterParams,
                count: hostNums.value,
                label_names: details.resource_spec.proxy.labels.map((item: { value: string }) => item.value),
                labels: details.resource_spec.proxy.labels.map((item: { id: number }) => String(item.id)),
              },
            },
          };
        }

        delete details.resource_spec;
        return {
          ...details,
          // disaster_tolerance_level: affinity,
          nodes: {
            backend: formatNodes(formData.details.nodes.backend),
            proxy: formatNodes(formData.details.nodes.proxy),
          },
        };
      };

      const params = {
        ...formData,
        details: getDetails(),
      };

      // 如果英文名为空新增业务英文名称接口，创建单据
      if (bizState.hasEnglishName) {
        handleCreateTicket(params);
      } else {
        handleCreateAppAbbr(params);
      }
    }
  };

  const handleResetFormdata = () => {
    _.merge(formData, getFormData());
    nextTick(() => {
      window.changeConfirm = false;
    });
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';
  @import '@styles/applyInstance.less';

  :deep(.item-input) {
    width: 435px;
  }

  .service-table {
    max-width: 932px !important;
  }

  .apply-form {
    .apply-form-database {
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
    .apply-form-quantity {
      margin-left: 15px;
      font-size: @font-size-normal;
      color: @default-color;
    }
  }

  .resource-pool-item {
    width: 655px;
    padding: 24px 0;
    background-color: #f5f7fa;
    border-radius: 2px;

    :deep(.bk-form-item) {
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
</style>
