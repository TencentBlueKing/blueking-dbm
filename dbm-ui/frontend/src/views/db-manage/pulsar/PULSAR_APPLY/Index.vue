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
    class="apply-pulsar"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      :model="formData"
      :rules="rules">
      <DbCard :title="t('基本信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          perrmision-action-id="pulsar_apply"
          @change-biz="handleChangeBiz" />
        <ClusterName
          v-model="formData.details.cluster_name"
          :biz-id="formData.bk_biz_id"
          :cluster-type="ClusterTypes.PULSAR"
          :db-app-abbr="formData.details.db_app_abbr" />
        <ClusterAlias
          v-model="formData.details.cluster_alias"
          :biz-id="formData.bk_biz_id"
          cluster-type="pulsar" />
      </DbCard>
      <RegionRequirements
        ref="regionRequirements"
        v-model="formData.details"
        @cloud-change="handleCloudChange" />
      <DbCard :title="t('部署需求')">
        <BkFormItem
          :label="t('Pulsar版本')"
          property="details.db_version"
          required>
          <DeployVersion
            v-model="formData.details.db_version"
            :db-type="DBTypes.PULSAR"
            query-key="pulsar" />
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
            <BkFormItem
              :label="t('Bookkeeper节点')"
              property="details.nodes.bookkeeper"
              required>
              <div>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.bookkeeper"
                  :disable-dialog-submit-method="ipSelectorDisabledSubmitMethods.bookkeeper"
                  :disable-host-method="bookkeeperDisableHostMethod"
                  :os-types="[OSTypes.Linux]"
                  required
                  style="display: inline-block"
                  @change="handleBookkeeperIpListChange">
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="至少n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56"> 2 </span>
                      <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                    </I18nT>
                  </template>
                  <template #desc>
                    {{ t('至少2台_建议规格至少为2核4G') }}
                  </template>
                </IpSelector>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="t('Zookeeper节点')"
              property="details.nodes.zookeeper"
              required>
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.zookeeper"
                :disable-dialog-submit-method="ipSelectorDisabledSubmitMethods.zookeeper"
                :disable-host-method="zookeeperDisableHostMethod"
                :os-types="[OSTypes.Linux]"
                required
                @change="handleZookeeperIpListChange">
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="需n台_已选n台"
                    style="font-size: 14px; color: #63656e"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56"> 3 </span>
                    <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
                <template #desc>
                  {{ t('需3台_建议规格至少为2核4G') }}
                </template>
              </IpSelector>
            </BkFormItem>
            <BkFormItem
              :label="t('Broker节点')"
              property="details.nodes.broker"
              required>
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.broker"
                :disable-dialog-submit-method="ipSelectorDisabledSubmitMethods.broker"
                :disable-host-method="brokerDisableHostMethod"
                :os-types="[OSTypes.Linux]"
                required
                @change="handleBrokerIpListChange">
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56"> 1 </span>
                    <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
                <template #desc>
                  {{ t('至少1台_建议规格至少为2核4G') }}
                </template>
              </IpSelector>
            </BkFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              :label="t('Bookkeeper节点')"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.bookkeeper.spec_id"
                  required>
                  <SpecSelector
                    ref="specBookkeeperRef"
                    v-model="formData.details.resource_spec.bookkeeper.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :city="formData.details.city_code"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="pulsar"
                    machine-type="pulsar_bookkeeper"
                    style="width: 314px"
                    :subzone-ids="formData.details.sub_zone_ids" />
                </BkFormItem>
                <ResourcePreview
                  v-model:tag-list="formData.details.resource_spec.bookkeeper.labels"
                  :biz-id="formData.bk_biz_id"
                  :params="{
                    city: formData.details.city_name,
                    subzones: formData.details.sub_zone_names.join('，'),
                    subzone_ids: formData.details.sub_zone_ids.join(','),
                    for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                    resource_types: [DBTypes.PULSAR, 'PUBLIC'],
                    spec_id: Number(formData.details.resource_spec.bookkeeper.spec_id),
                    labels: formData.details.resource_spec.bookkeeper.labels.map((item) => item.id).join(','),
                  }"
                  property="details.resource_spec.bookkeeper.labels" />
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.bookkeeper.count"
                  required>
                  <DbInput
                    v-model="formData.details.resource_spec.bookkeeper.count"
                    :min="2"
                    style="width: 314px"
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="t('Zookeeper节点')"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.zookeeper.spec_id"
                  required>
                  <SpecSelector
                    ref="specZookeeperRef"
                    v-model="formData.details.resource_spec.zookeeper.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :city="formData.details.city_code"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="pulsar"
                    machine-type="pulsar_zookeeper"
                    style="width: 314px"
                    :subzone-ids="formData.details.sub_zone_ids" />
                </BkFormItem>
                <ResourcePreview
                  v-model:tag-list="formData.details.resource_spec.zookeeper.labels"
                  :biz-id="formData.bk_biz_id"
                  :params="{
                    city: formData.details.city_name,
                    subzones: formData.details.sub_zone_names.join('，'),
                    subzone_ids: formData.details.sub_zone_ids.join(','),
                    for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                    resource_types: [DBTypes.PULSAR, 'PUBLIC'],
                    spec_id: Number(formData.details.resource_spec.zookeeper.spec_id),
                    labels: formData.details.resource_spec.zookeeper.labels.map((item) => item.id).join(','),
                  }"
                  property="details.resource_spec.zookeeper.labels" />
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.zookeeper.count"
                  required>
                  <DbInput
                    v-model="formData.details.resource_spec.zookeeper.count"
                    disabled
                    :min="3"
                    style="width: 314px"
                    type="number" />
                  <span class="input-desc">{{ t('需n台', { n: 3 }) }}</span>
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="t('Broker节点')"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="t('规格')"
                  property="details.resource_spec.broker.spec_id"
                  required>
                  <SpecSelector
                    ref="specBrokerRef"
                    v-model="formData.details.resource_spec.broker.spec_id"
                    :biz-id="formData.bk_biz_id"
                    :city="formData.details.city_code"
                    :cloud-id="formData.details.bk_cloud_id"
                    cluster-type="pulsar"
                    machine-type="pulsar_broker"
                    style="width: 314px"
                    :subzone-ids="formData.details.sub_zone_ids" />
                </BkFormItem>
                <ResourcePreview
                  v-model:tag-list="formData.details.resource_spec.broker.labels"
                  :biz-id="formData.bk_biz_id"
                  :params="{
                    city: formData.details.city_name,
                    subzones: formData.details.sub_zone_names.join('，'),
                    subzone_ids: formData.details.sub_zone_ids.join(','),
                    for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                    resource_types: [DBTypes.PULSAR, 'PUBLIC'],
                    spec_id: Number(formData.details.resource_spec.broker.spec_id),
                    labels: formData.details.resource_spec.broker.labels.map((item) => item.id).join(','),
                  }"
                  property="details.resource_spec.broker.labels" />
                <BkFormItem
                  :label="t('数量')"
                  property="details.resource_spec.broker.count"
                  required>
                  <DbInput
                    v-model="formData.details.resource_spec.broker.count"
                    :min="1"
                    style="width: 314px"
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="t('总容量')"
              required>
              <DbInput
                disabled
                :model-value="totalCapacity"
                style="width: 184px" />
              <span class="input-desc">G</span>
            </BkFormItem>
          </div>
        </Transition>
        <BkFormItem
          :label="t('Partition数量')"
          property="details.partition_num"
          required>
          <DbInput
            v-model="formData.details.partition_num"
            clearable
            :min="1"
            style="width: 185px"
            type="number" />
        </BkFormItem>
        <BkFormItem
          :label="t('消息保留')"
          property="details.retention_hours"
          required>
          <DbInput
            v-model="formData.details.retention_hours"
            clearable
            :min="1"
            style="width: 185px"
            type="number" />
          <span class="input-desc">{{ t('小时') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="t('副本数量')"
          property="details.replication_num"
          required>
          <DbInput
            v-model="formData.details.replication_num"
            clearable
            :max="ackQuorumMax"
            :min="2"
            style="width: 185px"
            type="number" />
          <span class="input-desc">{{ t('至少2_不能超过Bookkeeper数量') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="t('至少写入成功副本数量')"
          property="details.ack_quorum"
          required>
          <DbInput
            v-model="formData.details.ack_quorum"
            clearable
            :max="formData.details.replication_num || 2"
            :min="1"
            style="width: 185px"
            type="number" />
          <span class="input-desc">{{ t('当达到数量后_立即返回结果_减少用户等待时间') }}</span>
        </BkFormItem>
        <BkFormItem
          :label="t('访问端口')"
          property="details.port"
          required>
          <DbInput
            v-model="formData.details.port"
            clearable
            :min="1"
            style="width: 185px"
            type="number" />
        </BkFormItem>
        <EstimatedCost
          :params="{
            db_type: DBTypes.PULSAR,
            resource_spec: formData.details.resource_spec,
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
    <template #action>
      <div>
        <BkButton
          :loading="baseState.isSubmitting"
          style="width: 88px"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbResetButton
          class="ml-8"
          :confirm-handler="handleReset"
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
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { inject } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { Pulsar } from '@services/model/ticket/ticket';
  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { Affinity, ClusterTypes, DBTypes, OSTypes, TicketTypes } from '@common/const';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import DeployVersion from '@views/db-manage/common/apply-items/DeployVersion.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/BigData.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getInitFormdata = () => ({
    bk_biz_id: '' as number | '',
    details: {
      ack_quorum: 1,
      bk_cloud_id: 0,
      city_code: '',
      city_name: '',
      cluster_alias: '',
      cluster_name: '',
      db_app_abbr: '',
      db_version: '',
      disaster_tolerance_level: Affinity.MAX_EACH_ZONE_EQUAL, // 同 affinity
      ip_source: 'resource_pool',
      nodes: {
        bookkeeper: [] as HostInfo[],
        broker: [] as HostInfo[],
        zookeeper: [] as HostInfo[],
      },
      partition_num: 1,
      // password: '',
      port: 6650,
      replication_num: 2,
      resource_spec: {
        bookkeeper: {
          count: 2,

          labels: [] as {
            id: number;
            value: string;
          }[],

          spec_id: '',
        },
        broker: {
          count: 1,
          labels: [] as {
            id: number;
            value: string;
          }[],

          spec_id: '',
        },
        zookeeper: {
          count: 3,
          labels: [] as {
            id: number;
            value: string;
          }[],

          spec_id: '',
        },
      },
      retention_hours: 1,
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
      username: '',
    },
    remark: '',
    ticket_type: TicketTypes.PULSAR_APPLY,
  });

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);

  useTicketDetail<Pulsar.Apply>(TicketTypes.PULSAR_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
      });
      Object.assign(formData.details, {
        ack_quorum: details.ack_quorum,
        bk_cloud_id: details.bk_cloud_id,
        city_code: details.city_code,
        cluster_alias: details.cluster_alias,
        cluster_name: details.cluster_name,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        ip_source: details.ip_source,
        partition_num: details.partition_num,
        // password: details.password,
        port: details.port,
        replication_num: details.replication_num,
        retention_hours: details.retention_hours,
        username: details.username,
      });

      if (details.ip_source === 'resource_pool') {
        const resourceSpec = Object.entries(details.resource_spec!).reduce((prev, [specType, specInfo]) => {
          const labels = (specInfo.labels || []).map((labelItem, labelIndex) => ({
            id: Number(labelItem),
            value: specInfo.label_names[labelIndex],
          }));
          return Object.assign(prev, {
            [specType]: {
              count: specInfo.count,
              labels,
              spec_id: specInfo.spec_id,
            },
          });
        }, {});
        const subzoneIds = details.resource_spec!.zookeeper.location_spec.sub_zone_ids || [];
        Object.assign(formData.details, {
          resource_spec: Object.assign(formData.details.resource_spec, resourceSpec),
          sub_zone_ids: subzoneIds,
        });
        nextTick(() => {
          regionRequirementsRef.value!.setInitSubzone(subzoneIds);
        });
      }
    },
  });

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const formData = reactive(getInitFormdata());
  const formRef = ref();
  const specBookkeeperRef = ref();
  const specZookeeperRef = ref();
  const specBrokerRef = ref();
  const totalCapacity = ref(0);

  const ackQuorumMax = computed(() => {
    const max =
      formData.details.ip_source === 'resource_pool'
        ? formData.details.resource_spec.bookkeeper.count
        : formData.details.replication_num;
    return max || 2;
  });

  const rules = {
    'details.ack_quorum': [
      {
        message: t('写入成功副本数量小于等于副本数量'),
        trigger: 'change',
        validator: (value: number) => value <= formData.details.replication_num,
      },
    ],
    'details.nodes.bookkeeper': [
      {
        message: t('Bookkeeper节点数至少为2台'),
        trigger: 'change',
        validator: (value: Array<any>) => value.length >= 2,
      },
    ],
    'details.nodes.broker': [
      {
        message: t('Broker节点数至少为1台'),
        trigger: 'change',
        validator: (value: Array<any>) => value.length >= 1,
      },
    ],
    'details.nodes.zookeeper': [
      {
        message: t('Zookeeper节点数需3台'),
        trigger: 'change',
        validator: (value: Array<any>) => value.length === 3,
      },
    ],
    'details.replication_num': [
      {
        message: t('至少2_不能超过Bookkeeper数量'),
        trigger: 'change',
        validator: (value: number) => value <= ackQuorumMax.value,
      },
    ],
  };

  watch(
    () => formData.details.resource_spec.bookkeeper,
    () => {
      const count = Number(formData.details.resource_spec.bookkeeper.count);
      if (specBookkeeperRef.value) {
        const { storage_spec: storageSpec = [] } = specBookkeeperRef.value.getData();
        const disk = storageSpec.reduce((total: number, item: { min: number }) => total + Number(item.min || 0), 0);
        totalCapacity.value = disk * count;
      }
    },
    { deep: true, flush: 'post' },
  );

  /**
   * 切换业务，需要重置 IP 相关的选择
   */
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formData.details.nodes.bookkeeper = [];
    formData.details.nodes.broker = [];
    formData.details.nodes.zookeeper = [];
    serviceApply?.changeBizId(info.bk_biz_id);
  };
  /**
   * 变更所属管控区域
   */
  const handleCloudChange = (info: { id: number | string; name: string }) => {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formData.details.nodes.bookkeeper = [];
    formData.details.nodes.broker = [];
    formData.details.nodes.zookeeper = [];
  };

  const makeMapByHostId = (hostList: HostInfo[]) =>
    hostList.reduce(
      (result, item) => ({
        ...result,
        [item.host_id]: true,
      }),
      {} as Record<number, boolean>,
    );
  // IP 选择器提交校验方法
  const ipSelectorDisabledSubmitMethods = {
    bookkeeper: (hostList: Array<any>) => (hostList.length >= 2 ? false : t('至少n台', { n: 2 })),
    broker: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
    zookeeper: (hostList: Array<any>) => (hostList.length === 3 ? false : t('需n台', { n: 3 })),
  };
  // bookkeeper、zookeeper、broker 互斥
  const bookkeeperDisableHostMethod = (data: any) => {
    const zookeeperHostMap = makeMapByHostId(formData.details.nodes.zookeeper);
    if (zookeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Zookeeper']);
    }
    const brokerHostMap = makeMapByHostId(formData.details.nodes.broker);
    if (brokerHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Broker']);
    }

    return false;
  };
  // bookkeeper、zookeeper、broker 互斥
  const zookeeperDisableHostMethod = (data: any, list: any[] = []) => {
    const bookkeeperHostMap = makeMapByHostId(formData.details.nodes.bookkeeper);
    if (bookkeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Bookkeeper']);
    }
    const brokerHostMap = makeMapByHostId(formData.details.nodes.broker);
    if (brokerHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Broker']);
    }

    if (list.length >= 3 && !list.find((item) => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [3, list.length]);
    }

    return false;
  };
  // bookkeeper、zookeeper、broker 互斥
  const brokerDisableHostMethod = (data: any) => {
    const bookkeeperHostMap = makeMapByHostId(formData.details.nodes.bookkeeper);
    if (bookkeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Bookkeeper']);
    }
    const zookeeperHostMap = makeMapByHostId(formData.details.nodes.zookeeper);
    if (zookeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Zookeeper']);
    }

    return false;
  };
  // 更新 bookkeeper 节点
  const handleBookkeeperIpListChange = (data: HostInfo[]) => {
    formData.details.nodes.bookkeeper = data;
  };
  // 更新 zookeeper 节点
  const handleZookeeperIpListChange = (data: HostInfo[]) => {
    formData.details.nodes.zookeeper = data;
  };
  // 更新 broker 节点
  const handleBrokerIpListChange = (data: HostInfo[]) => {
    formData.details.nodes.broker = data;
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
      baseState.isSubmitting = true;
      const mapIpField = (ipList: HostInfo[]) =>
        ipList.map((item) => ({
          bk_biz_id: item.biz.id,
          bk_cloud_id: item.cloud_area.id,
          bk_host_id: item.host_id,
          ip: item.ip,
        }));

      const getDetails = () => {
        const details: Record<string, any> = _.cloneDeep(formData.details);

        if (formData.details.ip_source === 'resource_pool') {
          delete details.nodes;
          const regionAndDisasterParams = regionRequirementsRef.value!.getValue();
          return {
            ...details,
            resource_spec: {
              bookkeeper: {
                ...details.resource_spec.bookkeeper,
                ...specBookkeeperRef.value.getData(),
                ...regionAndDisasterParams,
                count: Number(details.resource_spec.bookkeeper.count),
                label_names: details.resource_spec.bookkeeper.labels.map((item: { value: string }) => item.value),
                labels: details.resource_spec.bookkeeper.labels.map((item: { id: number }) => String(item.id)),
              },
              broker: {
                ...details.resource_spec.broker,
                ...specBrokerRef.value.getData(),
                ...regionAndDisasterParams,

                count: Number(details.resource_spec.broker.count),
                label_names: details.resource_spec.broker.labels.map((item: { value: string }) => item.value),
                labels: details.resource_spec.broker.labels.map((item: { id: number }) => String(item.id)),
              },
              zookeeper: {
                ...details.resource_spec.zookeeper,
                ...specZookeeperRef.value.getData(),
                ...regionAndDisasterParams,
                count: Number(details.resource_spec.zookeeper.count),
                label_names: details.resource_spec.zookeeper.labels.map((item: { value: string }) => item.value),
                labels: details.resource_spec.zookeeper.labels.map((item: { id: number }) => String(item.id)),
              },
            },
          };
        }

        delete details.resource_spec;
        return {
          ...details,
          nodes: {
            bookkeeper: mapIpField(formData.details.nodes.bookkeeper),
            broker: mapIpField(formData.details.nodes.broker),
            zookeeper: mapIpField(formData.details.nodes.zookeeper),
          },
        };
      };

      const params = {
        ...formData,
        details: getDetails(),
      };
      // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
      if (bizState.hasEnglishName) {
        handleCreateTicket(params);
      } else {
        handleCreateAppAbbr(params);
      }
    });
  };

  /**
   * 重置表单
   */
  const handleReset = () => {
    Object.assign(formData, getInitFormdata());
    formRef.value.clearValidate();
    nextTick(() => {
      window.changeConfirm = false;
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

<style lang="less" scoped>
  .apply-pulsar {
    display: block;

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }

    :deep(.bk-radio-group) {
      width: 435px;

      .bk-radio-button {
        flex: auto;
      }
    }

    :deep(.item-input) {
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
  }
</style>
