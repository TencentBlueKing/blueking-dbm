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
    <div class="shared-cluster-apply">
      <DbForm
        ref="formRef"
        auto-label-width
        class="apply-form mb-32"
        :model="formData"
        :rules="rules">
        <DbCard :title="t('基本信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="mongodb_apply"
            @change-biz="handleChangeBiz" />
          <ClusterName
            v-model="formData.details.cluster_name"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
            :db-app-abbr="formData.details.db_app_abbr" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER" />
        </DbCard>
        <RegionRequirements
          ref="regionRequirements"
          v-model="formData.details"
          @cloud-change="handleCloudChange" />
        <DbCard :title="t('数据库部署信息')">
          <BkFormItem
            :label="t('MongoDB版本')"
            property="details.db_version"
            required>
            <BkSelect
              v-model="formData.details.db_version"
              class="item-input"
              filterable
              :input-search="false"
              :loading="getVersionsLoading">
              <BkOption
                v-for="versionItem in versionList || []"
                :key="versionItem"
                :label="versionItem"
                :value="versionItem" />
            </BkSelect>
          </BkFormItem>
          <BkFormItem
            :label="t('访问端口')"
            property="details.start_port"
            required>
            <DbInput
              v-model="formData.details.start_port"
              clearable
              :min="1"
              show-clear-only-hover
              style="width: 185px"
              type="number" />
          </BkFormItem>
        </DbCard>
        <DbCard :title="t('需求信息')">
          <BkFormItem
            label="Config Server"
            required>
            <div class="resource-pool-item">
              <BkFormItem
                :label="t('规格')"
                property="details.resource_spec.mongo_config.spec_id"
                required>
                <SpecSelector
                  ref="mongoCofigSpecRef"
                  v-model="formData.details.resource_spec.mongo_config.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :city="formData.details.city_code"
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="DBTypes.MONGODB"
                  :machine-type="MachineTypes.MONGO_CONFIG"
                  :subzone-ids="formData.details.sub_zone_ids" />
              </BkFormItem>
              <ResourcePreview
                v-model:tag-list="formData.details.resource_spec.mongo_config.labels"
                :biz-id="formData.bk_biz_id"
                :params="{
                  city: formData.details.city_name,
                  subzones: formData.details.sub_zone_names.join('，'),
                  subzone_ids: formData.details.sub_zone_ids.join(','),
                  for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                  resource_types: [DBTypes.MONGODB, 'PUBLIC'],
                  spec_id: Number(formData.details.resource_spec.mongo_config.spec_id),
                  labels: formData.details.resource_spec.mongo_config.labels.map((item) => item.id).join(','),
                }"
                property="details.resource_spec.mongo_config.labels" />
              <BkFormItem
                :label="t('数量')"
                property="details.resource_spec.mongo_config.count"
                required>
                <DbInput
                  v-model="formData.details.resource_spec.mongo_config.count"
                  disabled
                  type="number" />
                <span class="input-desc">{{ t('需要n台', { n: 3 }) }}</span>
              </BkFormItem>
            </div>
          </BkFormItem>
          <BkFormItem
            label="Mongos"
            required>
            <div class="resource-pool-item">
              <BkFormItem
                :label="t('规格')"
                property="details.resource_spec.mongos.spec_id"
                required>
                <SpecSelector
                  ref="mongosSpecRef"
                  v-model="formData.details.resource_spec.mongos.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :city="formData.details.city_code"
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="DBTypes.MONGODB"
                  :machine-type="MachineTypes.MONGOS"
                  :subzone-ids="formData.details.sub_zone_ids" />
              </BkFormItem>
              <ResourcePreview
                v-model:tag-list="formData.details.resource_spec.mongos.labels"
                :biz-id="formData.bk_biz_id"
                :params="{
                  city: formData.details.city_name,
                  subzones: formData.details.sub_zone_names.join('，'),
                  subzone_ids: formData.details.sub_zone_ids.join(','),
                  for_bizs: formData.bk_biz_id ? [formData.bk_biz_id, 0] : [0],
                  resource_types: [DBTypes.MONGODB, 'PUBLIC'],
                  spec_id: Number(formData.details.resource_spec.mongos.spec_id),
                  labels: formData.details.resource_spec.mongos.labels.map((item) => item.id).join(','),
                }"
                property="details.resource_spec.mongos.labels" />
              <BkFormItem
                :label="t('数量')"
                property="details.resource_spec.mongos.count"
                required>
                <DbInput
                  v-model="formData.details.resource_spec.mongos.count"
                  :min="2"
                  type="number" />
                <span class="input-desc">{{ t('至少n台', { n: 2 }) }}</span>
              </BkFormItem>
            </div>
          </BkFormItem>
          <BkFormItem
            label="ShardSvr"
            required>
            <MongoConfigSpec
              v-model="formData.details.resource_spec.mongodb"
              v-model:apply-schema="applySchema"
              v-model:spec-data="mongoConfigSpecData"
              :params="{
                city_name: formData.details.city_name,
                city_code: formData.details.city_code,
                bk_biz_id: formData.bk_biz_id,
                sub_zone_ids: formData.details.sub_zone_ids,
                sub_zone_names: formData.details.sub_zone_names,
                bk_cloud_id: formData.details.bk_cloud_id,
              }" />
          </BkFormItem>
          <BkFormItem
            :label="t('每台主机 oplog 容量占比')"
            property="details.oplog_percent"
            required>
            <DbInput
              v-model="formData.details.oplog_percent"
              clearable
              :max="100"
              :min="0"
              show-clear-only-hover
              style="width: 185px"
              type="number">
              <template #suffix>%</template>
            </DbInput>
            <span class="input-desc">{{ t('预计容量nG', [estimatedCapacity]) }}</span>
          </BkFormItem>
          <EstimatedCost
            :params="{
              db_type: DBTypes.MONGODB,
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
        :confirm-handler="handleResetformData"
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
  import type { UnwrapRef } from 'vue';
  import { inject } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { Mongodb } from '@services/model/ticket/ticket';
  import { getVersions } from '@services/source/version';
  import type { BizItem } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { Affinity, ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';
  import { clusterNameSymbolRegx } from '@common/regex';

  import DbForm from '@components/db-form/index.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements-mongodb/Index.vue';
  import ResourcePreview from '@views/db-manage/common/apply-items/ResourcePreview.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { APPLY_SCHEME } from '@views/db-manage/common/apply-schema/Index.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import MongoConfigSpec from './components/MongoConfigSpec.vue';

  const initData = () => ({
    bk_biz_id: '' as number | '',
    details: {
      bk_cloud_id: 0,
      city_code: '',
      city_name: '',
      cluster_alias: '',
      cluster_name: '',
      cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
      db_app_abbr: '',
      db_version: '',
      disaster_tolerance_level: Affinity.CROSS_SUBZONE_WEAK,
      ip_source: 'resource_pool',
      oplog_percent: 10,
      resource_spec: {
        mongo_config: {
          count: 3,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '',
        },
        mongodb: {
          capacity: 0,
          count: 0,
          labels: [] as {
            id: number;
            value: string;
          }[],
          machine_group_shard_num: 0,
          shard_machine_group: 0,
          shard_node_count: 3,
          shards_num: 0,
          spec_id: 0,
        },
        mongos: {
          count: 2,
          labels: [] as {
            id: number;
            value: string;
          }[],
          spec_id: '',
        },
      },
      start_port: 27021,
      sub_zone_ids: [] as number[],
      sub_zone_names: [] as string[],
    },
    remark: '',
    ticket_type: TicketTypes.MONGODB_SHARD_APPLY,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);

  useTicketDetail<Mongodb.ShardApply>(TicketTypes.MONGODB_SHARD_APPLY, {
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
        cluster_type: details.cluster_type,
        db_version: details.db_version,
        disaster_tolerance_level: details.disaster_tolerance_level,
        ip_source: details.ip_source,
        oplog_percent: details.oplog_percent,
        start_port: details.start_port,
      });

      if (details.ip_source === 'resource_pool') {
        const resourceSpec = Object.entries(details.resource_spec!).reduce((prev, [specType, specInfo]) => {
          const labels = (specInfo.labels || []).map((labelItem, labelIndex) => ({
            id: Number(labelItem),
            value: specInfo.label_names[labelIndex],
          }));
          return Object.assign(prev, {
            [specType]: {
              ...formData.details.resource_spec[
                specType as keyof UnwrapRef<typeof formData>['details']['resource_spec']
              ],
              count: specInfo.count,
              labels,
              spec_id: specInfo.spec_id,
            },
          });
        }, {});
        const subzoneIds = details.resource_spec!.mongo_config.location_spec.sub_zone_ids || [];
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

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const formRef = ref<InstanceType<typeof DbForm>>();
  const mongoCofigSpecRef = ref<InstanceType<typeof SpecSelector>>();
  const mongosSpecRef = ref<InstanceType<typeof SpecSelector>>();

  const applySchema = ref<APPLY_SCHEME>(APPLY_SCHEME.AUTO);
  const mongoConfigSpecData = ref<ComponentProps<typeof MongoConfigSpec>['specData']>();
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });

  const formData = reactive(initData());

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const rules = {
    'details.cluster_name': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
        validator: (val: string) => clusterNameSymbolRegx.test(val),
      },
    ],
    'details.resource_spec.mongodb.capacity': [
      {
        message: t('集群容量需求不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    'details.resource_spec.mongodb.machine_group_shard_num': [
      {
        message: t('集群 Shard 数 / 机器组数，需要整除'),
        trigger: 'change',
        validator: () => {
          const { shard_machine_group: shardMachineGroup, shards_num: shardsNum } =
            formData.details.resource_spec.mongodb;
          if (shardMachineGroup && shardsNum) {
            return shardsNum % shardMachineGroup === 0;
          }
          return true;
        },
      },
    ],
    'details.resource_spec.mongodb.shard_machine_group': [
      {
        message: t('机器组数不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    'details.resource_spec.mongodb.shard_node_count': [
      {
        message: t('每个 Shard 节点数不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    'details.resource_spec.mongodb.shards_num': [
      {
        message: t('集群 Shard 数不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    'details.resource_spec.mongodb.spec_id': [
      {
        message: t('规格不能为空'),
        trigger: 'change',
        validator: (value: number) => !!value,
      },
    ],
    'details.resource_spec.mongos.count': [
      {
        message: t('至少n台', { n: 2 }),
        trigger: 'change',
        validator: (value: number) => value >= 2,
      },
    ],
  };

  const estimatedCapacity = computed(() => {
    const capacityPercentage = formData.details.oplog_percent;
    const capacity = formData.details.resource_spec.mongodb.capacity || 0;

    return Math.round(capacity * (capacityPercentage / 100));
  });

  const resourceSepc = computed(
    () =>
      ({
        mongo_config: {
          count: formData.details.resource_spec.mongo_config.count,
          spec_id: formData.details.resource_spec.mongo_config.spec_id,
        },
        mongodb: {
          count: formData.details.resource_spec.mongodb.count,
          spec_id: formData.details.resource_spec.mongodb.spec_id,
        },
        mongos: {
          count: formData.details.resource_spec.mongos.count,
          spec_id: formData.details.resource_spec.mongos.spec_id,
        },
      }) as ComponentProps<typeof EstimatedCost>['params']['resource_spec'],
  );

  watch(
    () => [
      formData.details.resource_spec.mongodb.shards_num,
      formData.details.resource_spec.mongodb.shard_machine_group,
    ],
    () => {
      formRef.value!.validate('details.resource_spec.mongodb.machine_group_shard_num');
    },
  );

  const { data: versionList, loading: getVersionsLoading } = useRequest(getVersions, {
    defaultParams: [{ query_key: DBTypes.MONGODB }],
  });

  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
    serviceApply?.changeBizId(info.bk_biz_id);
  };

  const handleCloudChange = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;
  };

  const handleResetformData = () => {
    Object.assign(formData, initData());
    nextTick(() => {
      window.changeConfirm = false;
    });
  };

  const handleSubmit = async () => {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const { details } = formData;
    const { resource_spec: resourceSpec } = details;
    const { mongo_config: mongoConfig, mongodb, mongos } = resourceSpec;
    const mongodbSpecData = mongoConfigSpecData.value as NonNullable<UnwrapRef<typeof mongoConfigSpecData>>;
    const regionAndDisasterParams = regionRequirementsRef.value!.getValue();

    const params = {
      ...formData,
      details: {
        ...details,
        resource_spec: {
          mongo_config: {
            count: mongoConfig.count,
            // spec_id: mongoConfig.spec_id,
            ...mongoCofigSpecRef.value!.getData(),
            ...regionAndDisasterParams,
            label_names: mongoConfig.labels.map((item: { value: string }) => item.value),
            labels: mongoConfig.labels.map((item: { id: number }) => String(item.id)),
          },
          mongodb: {
            // ...mongodb,
            ...regionAndDisasterParams,
            capacity: mongodb.capacity,
            count: mongodb.count,
            cpu: mongodbSpecData.cpu,
            instance_num: mongodbSpecData.instance_num,
            label_names: mongodb.labels.map((item: { value: string }) => item.value),
            labels: mongodb.labels.map((item: { id: number }) => String(item.id)),
            mem: mongodbSpecData.mem,
            spec_id: mongodb.spec_id,
            spec_name: mongodbSpecData.spec_name,
            storage_spec: mongodbSpecData.storage_spec,
          },
          mongos: {
            ...mongos,
            ...mongosSpecRef.value!.getData(),
            ...regionAndDisasterParams,
            label_names: mongos.labels.map((item: { value: string }) => item.value),
            labels: mongos.labels.map((item: { id: number }) => String(item.id)),
          },
        },
        shard_machine_group: mongodb.shard_machine_group,
        shard_num: mongodb.shards_num,
      },
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
  .apply-form {
    .apply-form-tips {
      font-size: @font-size-mini;
      color: @gray-color;

      :deep(.bk-button-text) {
        margin-left: 4px;
        font-size: @font-size-mini;
      }
    }

    .db-card {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .bk-form-item:last-child {
        margin-bottom: 0;
      }
    }

    .inline-box {
      display: inline-flex;
      width: 220px;
    }

    :deep(.bk-radio-group) {
      width: 435px;

      .bk-radio-button {
        flex: auto;
      }

      .bk-radio-button-label {
        width: 100%;
      }
    }
  }

  .shared-cluster-apply {
    .input-desc {
      margin-left: 12px;
      font-size: 12px;
      color: #63656e;
    }

    .item-input {
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
  }
</style>
