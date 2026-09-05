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
    class="apply-influxdb"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      class="mb-16"
      :model="formData"
      :rules="rules">
      <DbCard :title="t('基本信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          perrmision-action-id="influxdb_apply"
          @change-biz="handleChangeBiz" />
        <GroupItem
          v-model="formData.details.group_id"
          :biz-id="formData.bk_biz_id"
          @change="handleChangeGroup" />
      </DbCard>
      <RegionRequirements
        ref="regionRequirements"
        v-model="formData.details"
        @cloud-change="handleCloudChange" />
      <DbCard :title="t('部署需求')">
        <BkFormItem
          :label="t('InfluxDB版本')"
          property="details.db_version"
          required>
          <DeployVersion
            v-model="formData.details.db_version"
            :db-type="DBTypes.INFLUXDB"
            query-key="influxdb" />
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
          <BkFormItem
            v-if="formData.details.ip_source === 'manual_input'"
            class="service-item"
            label=" "
            property="details.nodes.influxdb"
            required>
            <div>
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.influxdb"
                :os-types="[OSTypes.Linux]"
                required
                style="display: inline-block"
                @change="handleIpChange">
                <template #desc>
                  {{ t('主机数数量即为实例数量_建议规格至少为2核4G') }}
                </template>
              </IpSelector>
            </div>
          </BkFormItem>
          <BkFormItem
            v-else
            :label="t('InfluxDB实例')"
            required>
            <div class="resource-pool-item">
              <BkFormItem
                :label="t('规格')"
                property="details.resource_spec.influxdb.spec_id"
                required>
                <SpecSelector
                  ref="specRef"
                  v-model="formData.details.resource_spec.influxdb.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :city="formData.details.city_code"
                  :cloud-id="formData.details.bk_cloud_id"
                  cluster-type="influxdb"
                  machine-type="influxdb"
                  style="width: 314px"
                  :subzone-ids="formData.details.sub_zone_ids" />
              </BkFormItem>
              <ResourcePreview
                v-model:tag-list="formData.details.resource_spec.influxdb.labels"
                :biz-id="formData.bk_biz_id"
                :params="{
                  city: formData.details.city_name,
                  subzones: formData.details.sub_zone_names.join('，'),
                  subzone_ids: formData.details.sub_zone_ids.join(','),
                  for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                  resource_types: [DBTypes.INFLUXDB, 'PUBLIC'],
                  spec_id: Number(formData.details.resource_spec.influxdb.spec_id),
                  labels: formData.details.resource_spec.influxdb.labels.map((item) => item.id).join(','),
                }"
                property="details.resource_spec.influxdb.labels" />
              <BkFormItem
                :label="t('数量')"
                property="details.resource_spec.influxdb.count"
                required>
                <DbInput
                  v-model="formData.details.resource_spec.influxdb.count"
                  :min="1"
                  type="number" />
              </BkFormItem>
            </div>
          </BkFormItem>
        </Transition>
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
            db_type: DBTypes.INFLUXDB,
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
  import { inject } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { Influxdb } from '@services/model/ticket/ticket';
  import { checkHost } from '@services/source/ipchooser';
  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { Affinity, DBTypes, OSTypes, TicketTypes } from '@common/const';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import DeployVersion from '@views/db-manage/common/apply-items/DeployVersion.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/BigData.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import GroupItem from './components/GroupItem.vue';

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getInitFormdata = () => ({
    bk_biz_id: '' as number | '',
    details: {
      bk_cloud_id: 0,
      city_code: '',
      city_name: '',
      db_app_abbr: '',
      db_version: '',
      disaster_tolerance_level: Affinity.MAX_EACH_ZONE_EQUAL, // 同 affinity
      group_id: '',
      ip_source: 'resource_pool',
      nodes: {
        influxdb: [] as HostInfo[],
      },
      port: 8080,
      resource_spec: {
        influxdb: {
          count: 1,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '',
        },
      },
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
    },
    remark: '',
    ticket_type: TicketTypes.INFLUXDB_APPLY,
  });

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const { applyBizInfo, baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);

  useTicketDetail<Influxdb.Apply>(TicketTypes.INFLUXDB_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
      });
      Object.assign(formData.details, {
        bk_cloud_id: details.bk_cloud_id,
        city_code: details.city_code,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        group_id: details.group_id,
        ip_source: details.ip_source,
        port: details.port,
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
        Object.assign(formData.details.resource_spec, resourceSpec);
      }
    },
  });

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const groupName = ref('');
  const formRef = ref();
  const specRef = ref();

  const formData = reactive(getInitFormdata());
  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });

  const rules = {
    'details.nodes.influxdb': [
      {
        message: t('请添加服务器'),
        required: true,
        trigger: 'change',
        validator: (value: Array<any>) => value.length >= 1,
      },
    ],
    'details.port': [
      {
        message: t('8088为服务内部占用端口'),
        trigger: 'blur',
        validator: (value: number) => value !== 8088,
      },
    ],
  };

  /**
   * 切换业务，需要重置 IP 相关的选择
   */
  function handleChangeBiz(info: BizItem) {
    const bizChanged = applyBizInfo(info);
    serviceApply?.changeBizId(info.bk_biz_id);
    if (!bizChanged) {
      return;
    }
    formData.details.group_id = '';
    formData.details.nodes.influxdb = [];
  }
  /**
   * 变更所属管控区域
   */
  function handleCloudChange(info: { id: number | string; name: string }) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formData.details.nodes.influxdb = [];
  }

  function handleChangeGroup({ name }: { name: string }) {
    groupName.value = name;
  }

  // 更新 bookkeeper 节点
  const handleIpChange = (data: ServiceReturnType<typeof checkHost>) => {
    formData.details.nodes.influxdb = data;
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
      baseState.isSubmitting = true;

      const getDetails = () => {
        const details: Record<string, any> = {
          ...markRaw(formData.details),
          group_name: groupName.value,
        };

        if (formData.details.ip_source === 'resource_pool') {
          delete details.nodes;
          const regionAndDisasterParams = regionRequirementsRef.value!.getValue();
          return {
            ...details,
            resource_spec: {
              influxdb: {
                ...details.resource_spec.influxdb,
                ...specRef.value.getData(),
                ...regionAndDisasterParams,
                count: Number(details.resource_spec.influxdb.count),
                label_names: details.resource_spec.influxdb.labels.map((item: { value: string }) => item.value),
                labels: details.resource_spec.influxdb.labels.map((item: { id: number }) => String(item.id)),
              },
            },
          };
        }

        delete details.resource_spec;
        return {
          ...details,
          nodes: {
            influxdb: formData.details.nodes.influxdb.map((item) => ({
              bk_biz_id: item.biz.id,
              bk_cloud_id: item.cloud_area.id,
              bk_host_id: item.host_id,
              ip: item.ip,
            })),
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
  .apply-influxdb {
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

    .service-item {
      :deep(.bk-form-label) {
        &::after {
          content: '';
        }
      }
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
          width: 314px;
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
