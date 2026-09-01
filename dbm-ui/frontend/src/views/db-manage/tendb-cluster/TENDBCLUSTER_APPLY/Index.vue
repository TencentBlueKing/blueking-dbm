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
    <div class="spider-apply-instance-page">
      <DbForm
        ref="formRef"
        auto-label-width
        :model="formData"
        :rules="rules">
        <DbCard :title="t('基本信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="tendbcluster_apply"
            @change-biz="handleChangeBiz" />
          <ClusterName
            v-model="formData.details.cluster_name"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :db-app-abbr="formData.details.db_app_abbr" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.TENDBCLUSTER" />
        </DbCard>
        <RegionRequirements
          ref="regionRequirements"
          v-model="formData.details" />
        <DbCard :title="t('部署需求')">
          <ModuleItem
            v-model="formData.details.db_module_id"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.TENDBCLUSTER" />
          <BkFormItem
            label="Spider Master"
            required>
            <div class="resource-pool-item">
              <BkFormItem
                :label="t('规格')"
                property="details.resource_spec.spider.spec_id"
                required>
                <SpecSelector
                  ref="specProxyRef"
                  v-model="formData.details.resource_spec.spider.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :city="formData.details.city_code"
                  :cloud-id="formData.details.bk_cloud_id"
                  cluster-type="tendbcluster"
                  machine-type="proxy"
                  :subzone-ids="formData.details.sub_zone_ids" />
              </BkFormItem>
              <ResourcePreview
                v-model:tag-list="formData.details.resource_spec.spider.labels"
                :biz-id="formData.bk_biz_id"
                :params="{
                  city: formData.details.city_name,
                  subzones: formData.details.sub_zone_names.join('，'),
                  subzone_ids: formData.details.sub_zone_ids.join(','),
                  for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                  resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
                  spec_id: Number(formData.details.resource_spec.spider.spec_id),
                  labels: formData.details.resource_spec.spider.labels.map((item) => item.id).join(','),
                }"
                property="details.resource_spec.spider.labels" />
              <BkFormItem
                :label="t('数量')"
                property="details.resource_spec.spider.count"
                required>
                <div>
                  <DbInput
                    v-model="formData.details.resource_spec.spider.count"
                    :min="2"
                    type="number" />
                  <span class="input-desc">{{ t('至少n台', { n: 2 }) }}</span>
                </div>
              </BkFormItem>
            </div>
          </BkFormItem>
          <BkFormItem
            :label="t('后端存储')"
            required>
            <BackendQPSSpec
              ref="specBackendRef"
              v-model="formData.details.resource_spec.backend_group"
              :biz-id="formData.bk_biz_id"
              :city-code="formData.details.city_code"
              :city-name="formData.details.city_name"
              :cloud-id="formData.details.bk_cloud_id"
              db-type="tendbcluster"
              machine-type="backend"
              :subzone-ids="formData.details.sub_zone_ids"
              :subzone-names="formData.details.sub_zone_names" />
          </BkFormItem>
          <BkFormItem
            :label="t('访问端口')"
            property="details.spider_port"
            required>
            <DbInput
              v-model="formData.details.spider_port"
              clearable
              :max="65535"
              :min="3306"
              style="width: 185px"
              type="number" />
            <span class="input-desc">
              {{ t('范围n_min_max', { n: 3306, min: 25000, max: 65535 }) }}
            </span>
          </BkFormItem>
          <EstimatedCost
            :params="{
              db_type: DBTypes.TENDBCLUSTER,
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
      <BkButton
        class="w-88"
        :loading="baseState.isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
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
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { inject } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { TendbCluster } from '@services/model/ticket/ticket';
  import type { BizItem } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { Affinity, ClusterTypes, DBTypes, TicketTypes } from '@common/const';
  import { clusterNameSymbolRegx } from '@common/regex';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import ModuleItem from '@views/db-manage/common/apply-items/ModuleItem.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/Index.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import BackendQPSSpec from './components/BackendQPSSpec.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const initData = () => ({
    bk_biz_id: '' as number | '',
    details: {
      bk_cloud_id: 0,
      city_code: '',
      city_name: '',
      cluster_alias: '',
      cluster_name: '',
      cluster_shard_num: 0,
      db_app_abbr: '',
      db_module_id: null as null | number,
      disaster_tolerance_level: Affinity.CROS_SUBZONE,
      remote_shard_num: 0,
      resource_spec: {
        backend_group: {
          affinity: '',
          capacity: '',
          count: 0,
          future_capacity: '',
          labels: [] as {
            id: number;
            value: string;
          }[],
          location_spec: {
            city: '',
            sub_zone_ids: [],
          },
          spec_id: '' as number | '',
        },
        spider: {
          count: 2,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '' as number | '',
        },
      },
      spider_port: 25000,
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
    },
    remark: '',
    ticket_type: TicketTypes.TENDBCLUSTER_APPLY,
  });

  // 基础设置
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);

  useTicketDetail<TendbCluster.Apply>(TicketTypes.TENDBCLUSTER_APPLY, {
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
        cluster_shard_num: details.cluster_shard_num,
        disaster_tolerance_level: details.disaster_tolerance_level,
        ip_source: details.ip_source,
        remote_shard_num: details.remote_shard_num,
        spider_port: details.spider_port,
      });

      if (details.ip_source === 'resource_pool') {
        const { spider } = details.resource_spec!;
        const spiderLabels = (spider.labels || []).map((labelItem, labelIndex) => ({
          id: Number(labelItem),
          value: spider.label_names[labelIndex],
        }));
        const resourceSpec = {
          backend_group: formData.details.resource_spec.backend_group,
          spider: {
            count: spider.count,
            labels: spiderLabels,
            spec_id: spider.spec_id,
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

      nextTick(() => {
        Object.assign(formData.details, {
          db_module_id: details.db_module_id,
        });
      });
    },
  });

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const formRef = ref();
  const specProxyRef = ref();
  const specBackendRef = ref<InstanceType<typeof BackendQPSSpec>>();

  const formData = reactive(initData());

  const rules = {
    'details.cluster_name': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (value: string) => clusterNameSymbolRegx.test(value),
      },
    ],
    'details.resource_spec.backend_group.count': [
      {
        message: t('数量不能为空'),
        validator: (value: number) => value > 0,
      },
    ],
    'details.spider_port': [
      {
        message: t('范围n_min_max', { max: 65535, min: 25000, n: 3306 }),
        trigger: 'change',
        validator: (value: number) => value === 3306 || (value >= 25000 && value <= 65535),
      },
    ],
  };

  const resourceSepc = computed(() => {
    const specInfo = specBackendRef.value?.getData();
    return {
      backend_group: {
        count: specInfo?.machine_pair || 0,
        spec_id: formData.details.resource_spec.backend_group.spec_id,
      },
      spider: {
        count: formData.details.resource_spec.spider.count,
        spec_id: formData.details.resource_spec.spider.spec_id,
      },
    } as ComponentProps<typeof EstimatedCost>['params']['resource_spec'];
  });

  /**
   * 变更业务
   */
  const handleChangeBiz = (info: BizItem) => {
    formData.details.db_module_id = null;
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
    serviceApply?.changeBizId(info.bk_biz_id);
  };

  /** 重置表单 */
  const handleResetFormdata = () => {
    Object.assign(formData, initData());
    nextTick(() => {
      window.changeConfirm = false;
    });
  };

  const handleSubmit = async () => {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const details: Record<string, any> = _.cloneDeep(formData.details);
      // 集群容量需求不需要提交
      // delete details.resource_spec.backend_group.capacity;
      // delete details.resource_spec.backend_group.future_capacity;

      const regionAndDisasterParams = regionRequirementsRef.value!.getValue();
      const specBackendInfo = specBackendRef.value!.getData();

      return {
        ...details,
        cluster_shard_num: Number(specBackendInfo.cluster_shard_num),
        // disaster_tolerance_level: details.resource_spec.backend_group.affinity,
        remote_shard_num: Number(specBackendInfo.cluster_shard_num) / specBackendInfo.machine_pair!,
        resource_spec: {
          backend_group: {
            ...details.resource_spec.backend_group,
            ...regionAndDisasterParams,
            count: specBackendInfo.machine_pair,
            label_names: details.resource_spec.backend_group.labels.map((item: { value: string }) => item.value),
            labels: details.resource_spec.backend_group.labels.map((item: { id: number }) => String(item.id)),
            spec_info: specBackendInfo,
          },
          spider: {
            ...details.resource_spec.spider,
            ...specProxyRef.value.getData(),
            ...regionAndDisasterParams,
            count: Number(details.resource_spec.spider.count),
            label_names: details.resource_spec.spider.labels.map((item: { value: string }) => item.value),
            labels: details.resource_spec.spider.labels.map((item: { id: number }) => String(item.id)),
          },
        },
      };
    };
    const params = {
      ...formData,
      details: getDetails(),
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

  .spider-apply-instance-page {
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
          .dbm-input {
            width: 314px !important;
          }
        }
      }
    }

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }
  }
</style>
