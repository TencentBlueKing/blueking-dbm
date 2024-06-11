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
  <SmartAction
    class="apply-doris-page"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      class="mb-16"
      :model="formData"
      :rules="rules">
      <DbCard :title="t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          perrmision-action-id="doris_apply"
          @change-biz="handleChangeBiz" />
        <ClusterName v-model="formData.details.cluster_name" />
        <ClusterAlias
          v-model="formData.details.cluster_alias"
          :biz-id="formData.bk_biz_id"
          cluster-type="doris" />
        <CloudItem
          v-model="formData.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <RegionItem
        ref="regionItemRef"
        v-model="formData.details.city_code" />
      <DbCard :title="t('部署需求')">
        <AffinityItem v-model="formData.details.disaster_tolerance_level" />
        <BkFormItem
          :label="t('Doris版本')"
          property="details.db_version"
          required>
          <DeployVersion
            v-model="formData.details.db_version"
            db-type="doris"
            query-key="doris" />
        </BkFormItem>
        <BkFormItem
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
        </BkFormItem>
        <Transition
          mode="out-in"
          name="dbm-fade">
          <div
            v-if="formData.details.ip_source === 'manual_input'"
            class="mb-24">
            <DbFormItem
              :label="t('Follower节点')"
              property="details.nodes.follower"
              required>
              <div>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.follower"
                  :disable-dialog-submit-method="followerDisableDialogSubmitMethod"
                  :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['observer', 'hot', 'cold'])"
                  required
                  :show-view="false"
                  style="display: inline-block"
                  @change="(data: HostDetails[]) => handleIpListChange(data, 'follower')">
                  <template #submitTips="{ hostList }">
                    <IpSelectorSubmitTips
                      keypath="需n台_已选n台"
                      :values="[3, hostList.length]" />
                  </template>
                  <template #desc>
                    {{ t('需n台', { n: 3 }) }}
                  </template>
                </IpSelector>
              </div>
              <RenderHostTable
                v-model:data="formData.details.nodes.follower"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
            <DbFormItem
              :label="t('Observer节点')"
              property="details.nodes.observer">
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.observer"
                :disable-dialog-submit-method="optionalNodeDisableDialogSubmitMethod"
                :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['follower', 'hot', 'cold'])"
                :show-view="false"
                @change="(data: HostDetails[]) => handleIpListChange(data, 'observer')">
                <template #submitTips="{ hostList }">
                  <IpSelectorSubmitTips
                    keypath="若选择至少需要n台，已选m台"
                    :values="[2, hostList.length]" />
                </template>
                <template #desc>
                  {{ t('若选择至少需要n台', [2]) }}
                </template>
              </IpSelector>
              <RenderHostTable
                v-model:data="formData.details.nodes.observer"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
            <BkFormItem label=" ">
              <BkAlert
                style="width: 655px"
                :theme="tipTheme"
                :title="t('请保证冷/热节点至少存在一种')" />
            </BkFormItem>
            <DbFormItem
              :label="t('热节点')"
              property="details.nodes.hot">
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.hot"
                :disable-dialog-submit-method="optionalNodeDisableDialogSubmitMethod"
                :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['observer', 'follower', 'cold'])"
                :show-view="false"
                @change="(data: HostDetails[]) => handleIpListChange(data, 'hot')">
                <template #submitTips="{ hostList }">
                  <IpSelectorSubmitTips
                    keypath="若选择至少需要n台，已选m台"
                    :values="[2, hostList.length]" />
                </template>
                <template #desc>
                  {{ t('若选择至少需要n台', [2]) }}
                </template>
              </IpSelector>
              <RenderHostTable
                v-model:data="formData.details.nodes.hot"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
            <DbFormItem
              :label="t('冷节点')"
              property="details.nodes.cold">
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.cold"
                :disable-dialog-submit-method="optionalNodeDisableDialogSubmitMethod"
                :disable-host-method="(data: HostDetails) => disableHostMethod(data, ['follower', 'observer', 'hot'])"
                :show-view="false"
                @change="(data: HostDetails[]) => handleIpListChange(data, 'cold')">
                <template #submitTips="{ hostList }">
                  <IpSelectorSubmitTips
                    keypath="若选择至少需要n台，已选m台"
                    :values="[2, hostList.length]" />
                </template>
                <template #desc>
                  {{ t('若选择至少需要n台', [2]) }}
                </template>
              </IpSelector>
              <RenderHostTable
                v-model:data="formData.details.nodes.cold"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              :label="t('Follower节点')"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.follower.spec_id"
                  required>
                  <SpecSelector
                    ref="specFollowerRef"
                    v-model="formData.details.resource_spec.follower.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="doris"
                    machine-type="doris_follower" />
                </BkFormItem>
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.follower.count"
                  required>
                  <BkInput
                    v-model="formData.details.resource_spec.follower.count"
                    disabled
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem :label="t('Observer节点')">
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.observer.spec_id">
                  <SpecSelector
                    ref="specObserverRef"
                    v-model="formData.details.resource_spec.observer.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="doris"
                    machine-type="doris_observer" />
                </BkFormItem>
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.observer.count">
                  <BkInput
                    v-model="formData.details.resource_spec.observer.count"
                    :min="0"
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem label=" ">
              <BkAlert
                style="width: 655px"
                :theme="tipTheme"
                :title="t('请保证冷/热节点至少存在一种')" />
            </BkFormItem>
            <BkFormItem :label="t('热节点')">
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.hot.spec_id">
                  <SpecSelector
                    ref="specHotRef"
                    v-model="formData.details.resource_spec.hot.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="doris"
                    machine-type="doris_backend" />
                </BkFormItem>
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.hot.count">
                  <BkInput
                    v-model="formData.details.resource_spec.hot.count"
                    :min="0"
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem :label="t('冷节点')">
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.cold.spec_id">
                  <SpecSelector
                    ref="specColdRef"
                    v-model="formData.details.resource_spec.cold.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="doris"
                    machine-type="doris_backend" />
                </BkFormItem>
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.cold.count">
                  <BkInput
                    v-model="formData.details.resource_spec.cold.count"
                    :min="0"
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem :label="t('总容量')">
              <BkInput
                disabled
                :model-value="totalCapacity"
                style="width: 184px" />
              <span class="input-desc">G</span>
            </BkFormItem>
          </div>
        </Transition>
        <BkFormItem
          :label="t('查询端口')"
          property="details.query_port"
          required>
          <BkInput
            v-model="formData.details.query_port"
            clearable
            :max="65535"
            :min="1024"
            show-clear-only-hover
            style="width: 185px"
            type="number" />
          <span class="input-desc">{{ t('范围min_max', { min: 1024, max: 65535 }) }}</span>
        </BkFormItem>
        <BkFormItem
          :label="t('http端口')"
          property="details.http_port"
          required>
          <BkInput
            v-model="formData.details.http_port"
            clearable
            :max="65535"
            :min="1024"
            show-clear-only-hover
            style="width: 185px"
            type="number" />
          <span class="input-desc">{{ t('范围min_max', { min: 1024, max: 65535 }) }}</span>
        </BkFormItem>
        <BkFormItem :label="t('备注')">
          <BkInput
            v-model="formData.remark"
            :maxlength="100"
            :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
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
          class="ml8 w-88"
          :disabled="baseState.isSubmitting"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
        <BkButton
          class="ml8 w-88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { BizItem, HostDetails } from '@services/types';

  import { useApplyBase } from '@hooks';

  import { TicketTypes } from '@common/const';

  import AffinityItem from '@components/apply-items/AffinityItem.vue';
  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import DeployVersion from '@components/apply-items/DeployVersion.vue';
  import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import RenderHostTable from '@components/cluster-common/big-data-host-table/RenderHostTable.vue';
  import DbForm from '@components/db-form/index.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';
  import IpSelectorSubmitTips from '@components/ip-selector-submit-tips/Index.vue';

  type NodeType = 'follower' | 'observer' | 'hot' | 'cold';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const makeMapByHostId = (hostList: HostDetails[]) =>
    hostList.reduce(
      (result, item) => ({
        ...result,
        [item.host_id]: true,
      }),
      {} as Record<number, boolean>,
    );

  const genDefaultFormData = () => ({
    bk_biz_id: '' as number | '',
    remark: '',
    ticket_type: TicketTypes.DORIS_APPLY,
    details: {
      bk_cloud_id: 0,
      db_app_abbr: '',
      cluster_name: '',
      cluster_alias: '',
      city_code: '',
      db_version: '',
      ip_source: 'resource_pool',
      disaster_tolerance_level: 'NONE', // 同 affinity
      nodes: {
        follower: [] as Array<HostDetails>,
        observer: [] as Array<HostDetails>,
        hot: [] as Array<HostDetails>,
        cold: [] as Array<HostDetails>,
      },
      resource_spec: {
        follower: {
          spec_id: '',
          count: 3,
        },
        observer: {
          spec_id: '',
          count: 0,
        },
        hot: {
          spec_id: '',
          count: 0,
        },
        cold: {
          spec_id: '',
          count: 0,
        },
      },
      query_port: 9030,
      http_port: 8030,
    },
  });

  const formRef = ref<InstanceType<typeof DbForm>>();
  const specFollowerRef = ref<InstanceType<typeof SpecSelector>>();
  const specObserverRef = ref<InstanceType<typeof SpecSelector>>();
  const specHotRef = ref<InstanceType<typeof SpecSelector>>();
  const specColdRef = ref<InstanceType<typeof SpecSelector>>();
  const regionItemRef = ref<InstanceType<typeof RegionItem>>();
  const totalCapacity = ref(0);
  const isClickSubmit = ref(false);
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });

  const formData = reactive(genDefaultFormData());

  const tipTheme = computed(() => {
    if (isClickSubmit.value === false) {
      return 'info';
    }

    let isPass = false;
    if (formData.details.ip_source === 'resource_pool') {
      const { hot, cold } = formData.details.resource_spec;
      isPass = Boolean(hot.spec_id && hot.count) || Boolean(cold.spec_id && cold.count);
    } else {
      const { hot, cold } = formData.details.nodes;
      isPass = hot.length > 0 || cold.length > 0;
    }

    return isPass ? 'info' : 'danger';
  });

  const rules = {
    'details.nodes.follower': [
      {
        validator: (value: Array<HostDetails>) => value.length === 3,
        message: t('固定为n台', [3]),
        trigger: 'change',
      },
    ],
    'details.nodes.observer': [
      {
        validator: (value: Array<HostDetails>) => {
          if (value.length === 0) {
            return true;
          }
          return value.length >= 2;
        },
        message: t('若选择至少需要n台', [2]),
        trigger: 'change',
      },
    ],
    'details.nodes.hot': [
      {
        validator: () => formData.details.nodes.hot.length > 0 || formData.details.nodes.cold.length > 0,
        message: t('请保证冷/热节点至少存在一种'),
        trigger: 'change',
      },
      {
        validator: (value: Array<HostDetails>) => {
          if (value.length === 0) {
            return true;
          }
          return value.length >= 2;
        },
        message: t('若选择至少需要n台', [2]),
        trigger: 'change',
      },
    ],
    'details.nodes.cold': [
      {
        validator: () => formData.details.nodes.hot.length > 0 || formData.details.nodes.cold.length > 0,
        message: t('请保证冷/热节点至少存在一种'),
        trigger: 'change',
      },
      {
        validator: (value: Array<HostDetails>) => {
          if (value.length === 0) {
            return true;
          }
          return value.length >= 2;
        },
        message: t('若选择至少需要n台', [2]),
        trigger: 'change',
      },
    ],
    'details.resource_spec.follower.count': [
      {
        validator: (value: number) => value === 3,
        message: t('固定为n台', [3]),
        trigger: 'change',
      },
    ],
    'details.resource_spec.observer.spec_id': [
      {
        validator: (value: number | string) => {
          if (formData.details.resource_spec.observer.count > 0) {
            return !!value;
          }
          return true;
        },
        message: t('规格不能为空'),
        trigger: 'change',
      },
    ],
    'details.resource_spec.observer.count': [
      {
        validator: (value: number) => {
          if (value === 0) {
            return true;
          }
          return value >= 2;
        },
        message: t('若选择至少需要n台', [2]),
        trigger: 'change',
      },
    ],
    'details.resource_spec.hot.spec_id': [
      {
        validator: (value: number | string) => {
          if (formData.details.resource_spec.hot.count > 0) {
            return !!value;
          }
          return true;
        },
        message: t('规格不能为空'),
        trigger: 'change',
      },
    ],
    'details.resource_spec.hot.count': [
      {
        validator: (value: number) => {
          if (value === 0) {
            return true;
          }
          return value >= 2;
        },
        message: t('若选择至少需要n台', [2]),
        trigger: 'change',
      },
    ],
    'details.resource_spec.cold.spec_id': [
      {
        validator: (value: number | string) => {
          if (formData.details.resource_spec.cold.count > 0) {
            return !!value;
          }
          return true;
        },
        message: t('规格不能为空'),
        trigger: 'change',
      },
    ],
    'details.resource_spec.cold.count': [
      {
        validator: (value: number) => {
          if (value === 0) {
            return true;
          }
          return value >= 2;
        },
        message: t('若选择至少需要n台', [2]),
        trigger: 'change',
      },
    ],
    'details.query_port': [
      {
        validator: (value: number) => value !== 9010 && value !== 9020,
        message: t('9010 和 9020 为服务内部占用端口'),
        trigger: 'change',
      },
      {
        validator: (value: number) => value !== formData.details.http_port,
        message: t('与http端口互斥'),
        trigger: 'change',
      },
    ],
    'details.http_port': [
      {
        validator: (value: number) => value !== 9010 && value !== 9020,
        message: t('9010 和 9020 为服务内部占用端口'),
        trigger: 'change',
      },
      {
        validator: (value: number) => value !== formData.details.query_port,
        message: t('与查询端口互斥'),
        trigger: 'change',
      },
    ],
  };

  watch(
    [() => formData.details.resource_spec.hot, () => formData.details.resource_spec.cold],
    ([newHotSpec, newColdSpec]) => {
      const hotCount = Number(newHotSpec.count);
      const coldCount = Number(newColdSpec.count);
      if (specHotRef.value && specColdRef.value) {
        const { storage_spec: hotStorageSpec = [] } = specHotRef.value.getData();
        const { storage_spec: coldStorageSpec = [] } = specColdRef.value.getData();
        const hotDisk = hotStorageSpec.reduce((total, item) => total + Number(item.size || 0), 0);
        const coldDisk = coldStorageSpec.reduce((total, item) => total + Number(item.size || 0), 0);
        totalCapacity.value = hotDisk * hotCount + coldCount * coldDisk;
      }
    },
    { flush: 'post', deep: true },
  );

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const { baseState, bizState, handleCreateAppAbbr, handleCreateTicket, handleCancel } = useApplyBase();

  // 切换业务，需要重置 IP 相关的选择
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formData.details.nodes.hot = [];
    formData.details.nodes.cold = [];
    formData.details.nodes.observer = [];
    formData.details.nodes.follower = [];
  };

  /**
   * 变更所属管控区域
   */
  const handleChangeCloud = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;

    formData.details.nodes.hot = [];
    formData.details.nodes.cold = [];
    formData.details.nodes.follower = [];
    formData.details.nodes.observer = [];
  };

  // 主机节点互斥
  const disableHostMethod = (data: HostDetails, mutexNodeTypes: NodeType[]) => {
    const tipMap = {
      follower: t('主机已被Follower节点使用'),
      observer: t('主机已被Observer节点使用'),
      hot: t('主机已被热节点使用'),
      cold: t('主机已被冷节点使用'),
    };

    for (const mutexNodeType of mutexNodeTypes) {
      const hostMap = makeMapByHostId(formData.details.nodes[mutexNodeType]);
      if (hostMap[data.host_id]) {
        return tipMap[mutexNodeType];
      }
    }
    return false;
  };

  // follower 节点 IP 选择器提交
  const followerDisableDialogSubmitMethod = (hostList: HostDetails[]) =>
    hostList.length === 3 ? false : t('需要n台', { n: 3 });
  // observer、hot、cold 节点 IP 选择器提交
  const optionalNodeDisableDialogSubmitMethod = (hostList: HostDetails[]) => {
    if (hostList.length === 0) {
      return false;
    }
    return hostList.length >= 2 ? false : t('若选择至少需要n台', [2]);
  };

  // 更新节点IP
  const handleIpListChange = (data: HostDetails[], nodeType: NodeType) => {
    formData.details.nodes[nodeType] = data;
  };

  // 提交
  const handleSubmit = () => {
    isClickSubmit.value = true;
    formRef.value!.validate().then(() => {
      if (tipTheme.value === 'danger' && formData.details.ip_source === 'resource_pool') {
        return Promise.reject(t('请保证冷/热节点至少存在一种'));
      }
      baseState.isSubmitting = true;

      const getNodeList = (ipList: Array<HostDetails>) =>
        ipList.map((item) => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          bk_biz_id: item.biz.id,
        }));

      const getDetails = () => {
        const { details }: { details: Record<string, any> } = _.cloneDeep(formData);
        const { cityCode } = regionItemRef.value!.getValue();

        if (formData.details.ip_source === 'resource_pool') {
          delete details.nodes;

          const regionAndDisasterParams = {
            affinity: details.disaster_tolerance_level,
            location_spec: {
              city: cityCode,
              sub_zone_ids: [],
            },
          };

          const result = {
            ...details,
            resource_spec: {
              follower: {
                ...details.resource_spec.follower,
                ...specFollowerRef.value!.getData(),
                ...regionAndDisasterParams,
                count: Number(details.resource_spec.follower.count),
              },
            },
          };

          const observerCount = Number(details.resource_spec.observer.count);
          const hotCount = Number(details.resource_spec.hot.count);
          const coldCount = Number(details.resource_spec.cold.count);
          if (observerCount > 0) {
            Object.assign(result.resource_spec, {
              observer: {
                ...details.resource_spec.observer,
                ...specObserverRef.value!.getData(),
                ...regionAndDisasterParams,
                count: observerCount,
              },
            });
          }
          if (hotCount > 0) {
            Object.assign(result.resource_spec, {
              hot: {
                ...details.resource_spec.hot,
                ...specHotRef.value!.getData(),
                ...regionAndDisasterParams,
                count: hotCount,
              },
            });
          }
          if (coldCount > 0) {
            Object.assign(result.resource_spec, {
              cold: {
                ...details.resource_spec.cold,
                ...specColdRef.value!.getData(),
                ...regionAndDisasterParams,
                count: coldCount,
              },
            });
          }
          return result;
        }

        delete details.resource_spec;
        return {
          ...details,
          nodes: {
            follower: getNodeList(formData.details.nodes.follower),
            observer: getNodeList(formData.details.nodes.observer),
            hot: getNodeList(formData.details.nodes.hot),
            cold: getNodeList(formData.details.nodes.cold),
          },
        };
      };

      const params = {
        ...formData,
        details: getDetails(),
      };
      // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
      bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
    });
  };

  // 重置表单
  const handleReset = () => {
    InfoBox({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        isClickSubmit.value = false;
        Object.assign(formData, genDefaultFormData());
        formRef.value!.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
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
  .apply-doris-page {
    display: block;

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }

    .bk-radio-group {
      width: 435px;

      .bk-radio-button {
        flex: auto;
      }
    }

    .item-input {
      width: 435px;
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
  }
</style>
