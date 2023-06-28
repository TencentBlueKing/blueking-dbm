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
    class="apply-kafka-page"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      :model="formData"
      :rules="rules"
      style="margin-bottom: 16px;">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <ClusterName v-model="formData.details.cluster_name" />
        <ClusterAlias v-model="formData.details.cluster_alias" />
        <CloudItem
          v-model="formData.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem
        v-model="formData.details.city_code" /> -->
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('kafka版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="formData.details.db_version"
            class="item-input"
            filterable
            :input-search="false"
            :loading="isDbVersionLoading">
            <BkOption
              v-for="item in dbVersionList"
              :key="item"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="$t('服务器选择')"
          property="details.ip_source"
          required>
          <BkRadioGroup
            v-model="formData.details.ip_source">
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
            v-if="formData.details.ip_source === 'manual_input'"
            class="mb-24">
            <DbFormItem
              label="Zookeeper"
              property="details.nodes.zookeeper"
              required>
              <div>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.zookeeper"
                  :disable-dialog-submit-method="zookeeperDisableDialogSubmitMethod"
                  :disable-host-method="zookeeperDisableHostMethod"
                  required
                  :show-view="false"
                  style="display: inline-block;"
                  @change="handleZookeeperChange">
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="需n台_已选n台"
                      style="font-size: 14px; color: #63656e;"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56;"> 3 </span>
                      <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                    </I18nT>
                  </template>
                  <template #desc>
                    {{ $t('需3台_建议规格至少2核4G') }}
                  </template>
                </IpSelector>
              </div>
              <RenderHostTable
                v-model:data="formData.details.nodes.zookeeper"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
            <DbFormItem
              label="Broker"
              property="details.nodes.broker"
              required>
              <div>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.broker"
                  :disable-host-method="brokerDisableHostMethod"
                  required
                  :show-view="false"
                  style="display: inline-block;"
                  @change="handleBrokerChange">
                  <template #desc>
                    {{ $t('至少1台_建议规格至少2核4G') }}
                  </template>
                </IpSelector>
              </div>
              <RenderHostTable
                v-model:data="formData.details.nodes.broker"
                :biz-id="formData.bk_biz_id" />
            </DbFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              label="Zookeeper"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="$t('规格')"
                  property="details.resource_spec.zookeeper.spec_id"
                  required>
                  <SpecSelector
                    ref="specZookeeperRef"
                    v-model="formData.details.resource_spec.zookeeper.spec_id"
                    cluster-type="kafka"
                    machine-type="zookeeper" />
                </BkFormItem>
                <BkFormItem
                  :label="$t('数量')"
                  property="details.resource_spec.zookeeper.count"
                  required>
                  <BkInput
                    v-model="formData.details.resource_spec.zookeeper.count"
                    disabled
                    :min="3"
                    type="number" />
                  <span class="input-desc">{{ $t('需n台', {n: 3}) }}</span>
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              label="Broker"
              required>
              <div class="resource-pool-item">
                <BkFormItem
                  :label="$t('规格')"
                  property="details.resource_spec.broker.spec_id"
                  required>
                  <SpecSelector
                    ref="specBrokerRef"
                    v-model="formData.details.resource_spec.broker.spec_id"
                    cluster-type="kafka"
                    machine-type="broker" />
                </BkFormItem>
                <BkFormItem
                  :label="$t('数量')"
                  property="details.resource_spec.broker.count"
                  required>
                  <BkInput
                    v-model="formData.details.resource_spec.broker.count"
                    :min="1"
                    type="number" />
                </BkFormItem>
              </div>
            </BkFormItem>
            <BkFormItem
              :label="$t('总容量')"
              required>
              <BkInput
                disabled
                :model-value="totalCapacity"
                style="width: 184px;" />
              <span class="input-desc">G</span>
            </BkFormItem>
          </div>
        </Transition>
        <BkFormItem
          :label="$t('访问端口')"
          property="details.port"
          required>
          <BkInput
            v-model="formData.details.port"
            clearable
            :min="1"
            show-clear-only-hover
            style="width: 185px;"
            type="number" />
          <span style="margin-left: 12px; font-size: 12px; color: #63656e;">
            {{ $t('范围1025_65535') }}
          </span>
        </BkFormItem>
        <BkFormItem
          :label="$t('Partition数量')"
          property="details.partition_num"
          required>
          <BkInput
            v-model="formData.details.partition_num"
            clearable
            :min="1"
            show-clear-only-hover
            style="width: 185px;"
            type="number" />
        </BkFormItem>
        <BkFormItem
          :label="$t('消息保留')"
          property="details.retention_hours"
          required>
          <BkInput
            v-model="formData.details.retention_hours"
            clearable
            :min="1"
            show-clear-only-hover
            style="width: 185px;"
            type="number" />
          <span style="margin-left: 12px; font-size: 12px; color: #63656e;">
            {{ $t('小时') }}
          </span>
        </BkFormItem>
        <BkFormItem
          :label="$t('副本数量')"
          property="details.replication_num"
          required>
          <BkInput
            v-model="formData.details.replication_num"
            clearable
            :min="1"
            show-clear-only-hover
            style="width: 185px;"
            type="number" />
          <span style="margin-left: 12px; font-size: 12px; color: #63656e;">
            {{ $t('需小于等于broker数量') }}
          </span>
        </BkFormItem>
        <BkFormItem
          :label="$t('备注')"
          property="remark">
          <BkInput
            v-model="formData.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px;"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
    <template #action>
      <div>
        <BkButton
          :loading="baseState.isSubmitting"
          style="width: 88px;"
          theme="primary"
          @click="handleSubmit">
          {{ $t('提交') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleReset">
          {{ $t('重置') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ $t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
</template>
<script setup lang="ts">
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types/common';
  import type { HostDetails } from '@services/types/ip';
  import { getVersions } from '@services/versionFiles';

  import {
    useApplyBase,
    useInfo,
  } from '@hooks';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import RenderHostTable, {
    type IHostTableData,
  } from '@components/cluster-common/big-data-host-table/RenderHostTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';
  const { t } = useI18n();

  const formatIpData = (data: Array<HostDetails>) => data.map(item => ({
    ...item,
    instance_num: 1,
  }));

  const genDefaultFormData = () => ({
    bk_biz_id: '' as '' | number,
    remark: '',
    ticket_type: 'KAFKA_APPLY',
    details: {
      bk_cloud_id: '',
      db_app_abbr: '',
      cluster_name: '',
      cluster_alias: '',
      city_code: '',
      db_version: '',
      ip_source: 'resource_pool',
      nodes: {
        zookeeper: [] as Array<IHostTableData>,
        broker: [] as Array<IHostTableData>,
      },
      resource_spec: {
        zookeeper: {
          spec_id: '',
          count: 3,
        },
        broker: {
          spec_id: '',
          count: 1,
        },
      },
      port: 5000,
      partition_num: 1,
      retention_hours: 1,
      replication_num: 1,
    },
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');
  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });

  const rules = {
    'details.nodes.zookeeper': [
      {
        validator: (value: Array<any>) => value.length === 3,
        message: t('Zookeeper需3台'),
        trigger: 'change',
      },
    ],
    'details.nodes.broker': [
      {
        validator: (value: Array<any>) => value.length > 0,
        message: t('Broker不能为空'),
        trigger: 'change',
      },
    ],
    'details.port': [
      {
        validator: (value: number) => value >= 1025 && value <= 65535,
        message: t('访问端口范围1025_65535'),
        trigger: 'change',
      },
    ],
    'details.replication_num': [
      {
        validator: (value: number) => {
          if (formData.details.ip_source === 'resource_pool') {
            return value <= formData.details.resource_spec.broker.count;
          }
          return value <= formData.details.nodes.broker.length;
        },
        message: t('副本数需小于等于Broker数量'),
        trigger: 'change',
      },
    ],
    'details.resource_spec.zookeeper.count': [
      {
        validator: (value: number) => value % 2 === 1,
        message: t('至少3台_且为奇数'),
        trigger: 'change',
      },
    ],
  };
  const formRef = ref();
  const specZookeeperRef = ref();
  const specBrokerRef = ref();
  const isDbVersionLoading = ref(true);
  const dbVersionList = shallowRef<Array<string>>([]);
  const formData = reactive(genDefaultFormData());
  const totalCapacity = ref(0);

  watch(() => formData.details.resource_spec.broker, () => {
    const count = Number(formData.details.resource_spec.broker.count);
    if (specBrokerRef.value) {
      const { storage_spec: storageSpec = [] } = specBrokerRef.value.getData();
      const disk = storageSpec.reduce((total: number, item: { size: number }) => total + Number(item.size || 0), 0);
      totalCapacity.value = disk * count;
    }
  }, { flush: 'post', deep: true });

  // 获取 DB 版本列表
  getVersions({
    query_key: 'kafka',
  }).then((data) => {
    dbVersionList.value = data;
  })
    .finally(() => {
      isDbVersionLoading.value = false;
    });

  const {
    baseState,
    bizState,
    handleCreateAppAbbr,
    handleCreateTicket,
    handleCancel,
  } = useApplyBase();

  const zookeeperDisableDialogSubmitMethod = (hostList: Array<any>) => (hostList.length !== 3 ? t('zookeeper需3台') : false);

  const zookeeperDisableHostMethod = (data: any, list: any[]) => {
    if (list.length >= 3 && !list.find(item => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [3, list.length]);
    }

    return false;
  };

  const brokerDisableHostMethod = (data: any) => {
    const zookeeperHostIdMap = formData.details.nodes.zookeeper.reduce((result, item) => ({
      ...result,
      [item.host_id]: true,
    }), {} as Record<number, boolean>);

    return zookeeperHostIdMap[data.host_id] ? t('主机已被zooeeper使用') : false;
  };

  // 切换业务，需要重置 IP 相关的选择
  function handleChangeBiz(info: BizItem) {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formData.details.nodes.zookeeper = [];
    formData.details.nodes.broker = [];
  }
  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formData.details.nodes.zookeeper = [];
    formData.details.nodes.broker = [];
  }

  const handleZookeeperChange = (data: Array<HostDetails>) => {
    formData.details.nodes.zookeeper = formatIpData(data);
  };

  const handleBrokerChange = (data: Array<HostDetails>) => {
    formData.details.nodes.broker = formatIpData(data);
  };

  // 提交
  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        baseState.isSubmitting = true;
        const mapIpField = (ipList: Array<IHostTableData>) => ipList.map(item => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          bk_biz_id: item.biz.id,
        }));

        const getDetails = () => {
          const details: Record<string, any> = { ...markRaw(formData.details) };

          if (formData.details.ip_source === 'resource_pool') {
            delete details.nodes;
            return {
              ...details,
              resource_spec: {
                zookeeper: {
                  ...details.resource_spec.zookeeper,
                  ...specZookeeperRef.value.getData(),
                  count: Number(details.resource_spec.zookeeper.count),
                },
                broker: {
                  ...details.resource_spec.broker,
                  ...specBrokerRef.value.getData(),
                  count: Number(details.resource_spec.broker.count),
                },
              },
            };
          }

          delete details.resource_spec;
          return {
            ...details,
            nodes: {
              zookeeper: mapIpField(formData.details.nodes.zookeeper),
              broker: mapIpField(formData.details.nodes.broker),
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
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, genDefaultFormData());
        formRef.value.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };
</script>
<style lang="less">
  .apply-kafka-page {
    display: block;

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
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
</style>
