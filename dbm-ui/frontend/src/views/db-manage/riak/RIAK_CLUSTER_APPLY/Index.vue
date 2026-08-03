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
    class="apply-riak-page"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      class="mb-32"
      :model="formData"
      :rules="formRules">
      <DbCard :title="t('基本信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          perrmision-action-id="riak_cluster_apply"
          @change-biz="handleChangeBiz" />
        <ModuleItem
          v-model="formData.details.db_module_id"
          v-model:module-alias-name="moduleAliasName"
          :biz-id="formData.bk_biz_id"
          :cluster-type="ClusterTypes.RIAK" />
        <ClusterName
          v-model="formData.details.cluster_name"
          :biz-id="formData.bk_biz_id"
          :cluster-type="ClusterTypes.RIAK"
          :db-app-abbr="formData.details.db_app_abbr"
          :db-module-id="formData.details.db_module_id"
          :db-module-name="moduleAliasName" />
        <ClusterAlias
          v-model="formData.details.cluster_alias"
          :biz-id="formData.bk_biz_id"
          cluster-type="riak" />
      </DbCard>
      <RegionRequirements
        ref="regionRequirements"
        v-model="formData.details"
        @cloud-change="handleCloudChange" />
      <DbCard :title="t('数据库部署信息')">
        <BkFormItem
          :label="t('Riak版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="formData.details.db_version"
            class="item-input"
            disabled
            :input-search="false"
            style="width: 185px">
            <BkOption
              v-for="item in dbVersionList"
              :key="item"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <!-- <BkFormItem
          :label="t('访问端口')"
          property="details.http_port"
          required>
          <BkInput
            v-model="formData.details.http_port"
            disabled
            style="width: 185px;"
            type="number" />
        </BkFormItem> -->
      </DbCard>
      <DbCard :title="t('部署需求')">
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
            v-if="formData.details.ip_source === 'resource_pool'"
            class="mb-24">
            <BkFormItem
              :label="t('资源规格')"
              property="details.resource_spec.riak.spec_id"
              required>
              <SpecSelector
                ref="specRef"
                v-model="formData.details.resource_spec.riak.spec_id"
                :biz-id="formData.bk_biz_id"
                :city="formData.details.city_code"
                :cloud-id="formData.details.bk_cloud_id"
                :cluster-type="ClusterTypes.RIAK"
                machine-type="riak"
                style="width: 435px"
                :subzone-ids="formData.details.sub_zone_ids" />
            </BkFormItem>
            <ResourcePreview
              v-model:tag-list="formData.details.resource_spec.riak.labels"
              :biz-id="formData.bk_biz_id"
              :params="{
                city: formData.details.city_name,
                subzones: formData.details.sub_zone_names.join('，'),
                subzone_ids: formData.details.sub_zone_ids.join(','),
                for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                resource_types: [DBTypes.RIAK, 'PUBLIC'],
                spec_id: Number(formData.details.resource_spec.riak.spec_id),
                labels: formData.details.resource_spec.riak.labels.map((item) => item.id).join(','),
              }"
              property="details.resource_spec.riak.labels" />
            <BkFormItem
              :label="t('节点数量')"
              property="details.resource_spec.riak.count"
              required>
              <BkInput
                v-model="formData.details.resource_spec.riak.count"
                clearable
                :min="3"
                show-clear-only-hover
                style="width: 185px"
                type="number" />
            </BkFormItem>
          </div>
          <div
            v-else
            class="mb-24">
            <BkFormItem
              ref="nodesRef"
              :label="t('服务器')"
              property="details.nodes"
              required>
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes"
                :disable-dialog-submit-method="disableHostSubmitMethods"
                :os-types="[OSTypes.Linux]"
                @change="handleProxyIpChange">
                <template #desc>
                  {{ t('至少n台', { n: 3 }) }}
                </template>
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56"> 3 </span>
                    <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
              </IpSelector>
            </BkFormItem>
          </div>
        </Transition>
        <EstimatedCost
          :params="{
            db_type: DBTypes.RIAK,
            resource_spec: resourceSepc,
          }" />
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
          :loading="baseState.isSubmitting"
          style="width: 88px"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :disabled="baseState.isSubmitting"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
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
  import InfoBox from 'bkui-vue/lib/info-box';
  import { inject } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Riak } from '@services/model/ticket/ticket';
  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { Affinity, ClusterTypes, DBTypes, OSTypes, TicketTypes } from '@common/const';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import ModuleItem from '@views/db-manage/common/apply-items/ModuleItem.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/BigData.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  // 目前固定为此版本
  const dbVersionList = [2.2];

  const genDefaultFormData = () => ({
    bk_biz_id: '' as number | '',
    details: {
      bk_cloud_id: 0,
      city_code: '',
      city_name: '',
      cluster_alias: '',
      cluster_name: '',
      db_app_abbr: '',
      db_module_id: null as number | null,
      db_version: '2.2',
      disaster_tolerance_level: Affinity.MAX_EACH_ZONE_EQUAL, // 同 affinity
      ip_source: 'resource_pool',
      nodes: [] as HostInfo[],
      resource_spec: {
        riak: {
          count: 3,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '',
        },
      },
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
      // http_port: 8087,
    },
    remark: '',
    ticket_type: TicketTypes.RIAK_CLUSTER_APPLY,
  });

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);

  useTicketDetail<Riak.Apply>(TicketTypes.RIAK_CLUSTER_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
      });
      Object.assign(formData.details, {
        bk_cloud_id: details.bk_cloud_id,
        city_code: details.city_code,
        cluster_alias: details.cluster_alias,
        cluster_name: details.cluster_name,
        db_module_id: details.db_module_id,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        ip_source: details.ip_source,
      });

      if (details.ip_source === 'resource_pool') {
        const { riak } = details.resource_spec!;
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
        const subzoneIds = riak.location_spec.sub_zone_ids || [];
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

  const formRef = ref();
  const specRef = ref();
  const nodesRef = ref();
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });
  const moduleAliasName = ref('');
  const formData = reactive(genDefaultFormData());

  const formRules = {
    'details.nodes': [
      {
        message: t('节点数至少为n台', [3]),
        trigger: 'change',
        validator: (value: HostInfo[]) => value.length >= 3,
      },
    ],
    'details.resource_spec.riak.count': [
      {
        message: t('节点数至少为n台', [3]),
        trigger: 'change',
        validator: (value: number) => value >= 3,
      },
    ],
  };

  const resourceSepc = computed(
    () =>
      ({
        riak: {
          count: formData.details.resource_spec.riak.count,
          spec_id: formData.details.resource_spec.riak.spec_id,
        },
      }) as ComponentProps<typeof EstimatedCost>['params']['resource_spec'],
  );

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  // 切换业务，需要重置 IP 相关的选择
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
    serviceApply?.changeBizId(info.bk_biz_id);
  };

  const handleCloudChange = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;

    formData.details.nodes = [];
  };

  const disableHostSubmitMethods = (hostList: Array<HostInfo[]>) =>
    hostList.length < 3 ? t('至少n台', { n: 3 }) : false;

  const handleProxyIpChange = (data: HostInfo[]) => {
    formData.details.nodes = data;
    if (formData.details.nodes.length > 0) {
      nodesRef.value.clearValidate();
    }
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
      baseState.isSubmitting = true;

      const params = {
        ...formData,
        details: {
          ...formData.details,
          db_module_name: moduleAliasName.value,
        },
      };

      if (formData.details.ip_source === 'resource_pool') {
        Object.assign(params.details, {
          resource_spec: {
            riak: {
              ...specRef.value.getData(),
              ...regionRequirementsRef.value!.getValue(),
              count: formData.details.resource_spec.riak.count,
              label_names: formData.details.resource_spec.riak.labels.map((item: { value: string }) => item.value),
              labels: formData.details.resource_spec.riak.labels.map((item: { id: number }) => String(item.id)),
            },
          },
        });
      } else {
        Object.assign(params.details, {
          nodes: {
            riak: formData.details.nodes.map((nodeItem) => ({
              bk_cloud_id: nodeItem.cloud_id,
              bk_host_id: nodeItem.host_id,
              ip: nodeItem.ip,
            })),
          },
        });
      }

      // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
      if (bizState.hasEnglishName) {
        handleCreateTicket(params);
      } else {
        handleCreateAppAbbr(params);
      }
    });
  };

  const handleReset = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, genDefaultFormData());
        formRef.value.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
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
  .apply-riak-page {
    display: block;

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }

    .item-input {
      width: 435px;
    }
  }
</style>
