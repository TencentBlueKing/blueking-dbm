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
        <DbCard :title="t('业务信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            @change-biz="handleChangeBiz" />
          <ClusterName v-model="formData.details.cluster_name" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER" />
          <CloudItem
            v-model="formData.details.bk_cloud_id"
            @change="handleChangeCloud" />
        </DbCard>
        <RegionItem
          ref="regionItemRef"
          v-model="formData.details.city_code" />
        <DbCard :title="t('数据库部署信息')">
          <AffinityItem v-model="formData.details.disaster_tolerance_level" />
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
            <BkInput
              v-model="formData.details.start_port"
              clearable
              :min="1"
              show-clear-only-hover
              style="width: 185px;"
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
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
                  :machine-type="MachineTypes.MONGO_CONFIG"
                  style="width: 314px;" />
              </BkFormItem>
              <BkFormItem
                :label="t('数量')"
                property="details.resource_spec.mongo_config.count"
                required>
                <BkInput
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
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
                  :machine-type="MachineTypes.MONGOS"
                  style="width: 314px;" />
              </BkFormItem>
              <BkFormItem
                :label="t('数量')"
                property="details.resource_spec.mongos.count"
                required>
                <BkInput
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
              ref="mongoConfigSpecRef"
              v-model="formData.details.resource_spec.mongodb"
              :biz-id="formData.bk_biz_id"
              :cloud-id="formData.details.bk_cloud_id"
              :properties="{
                capacity: 'details.resource_spec.mongodb.capacity',
                specId: 'details.resource_spec.mongodb.spec_id'
              }"
              @current-change="handleMongoConfigSpecChange" />
          </BkFormItem>
          <BkFormItem
            :label="t('每台主机oplog容量占比')"
            property="details.oplog_percent"
            required>
            <BkInput
              v-model="formData.details.oplog_percent"
              clearable
              :max="100"
              :min="0"
              show-clear-only-hover
              style="width: 185px;"
              suffix="%"
              type="number" />
            <span class="input-desc">{{ t('预计容量nG', [estimatedCapacity]) }}</span>
          </BkFormItem>
          <BkFormItem :label="t('备注')">
            <BkInput
              v-model="formData.remark"
              :maxlength="100"
              :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
              style="width: 655px;"
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
        @click="handleResetformData">
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
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterSpecModel from '@services/model/resource-spec/cluster-sepc';
  import { getVersions } from '@services/source/version';
  import type { BizItem } from '@services/types';

  import {
    useApplyBase,
    useInfo,
  } from '@hooks';

  import {
    ClusterTypes,
    DBTypes,
    MachineTypes,
    TicketTypes,
  } from '@common/const';
  import { nameRegx } from '@common/regex';

  import AffinityItem from '@components/apply-items/AffinityItem.vue';
  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import DbForm from '@components/db-form/index.vue';

  import MongoConfigSpec from '@views/mongodb-manage/components/MongoConfigSpec.vue';

  const initData = () => ({
    bk_biz_id: '' as number | '',
    ticket_type: TicketTypes.MONGODB_SHARD_APPLY,
    remark: '',
    details: {
      cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
      bk_cloud_id: 0,
      db_app_abbr: '',
      cluster_name: '',
      cluster_alias: '',
      city_code: '',
      db_version: '',
      start_port: 27021,
      oplog_percent: 10,
      ip_source: 'resource_pool',
      disaster_tolerance_level: 'NONE',
      resource_spec: {
        mongo_config: {
          spec_id: '',
          count: 3,
        },
        mongos: {
          spec_id: '',
          count: 2,
        },
        mongodb: {
          spec_id: '',
          count: 0,
          capacity: 0,
        },
      },
    },
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const {
    baseState,
    bizState,
    handleCancel,
    handleCreateAppAbbr,
    handleCreateTicket,
  } = useApplyBase();

  const formRef = ref<InstanceType<typeof DbForm>>();
  const regionItemRef = ref<InstanceType<typeof RegionItem>>();
  const mongoCofigSpecRef = ref<InstanceType<typeof SpecSelector>>();
  const mongosSpecRef = ref<InstanceType<typeof SpecSelector>>();
  const mongoConfigSpecRef = ref<InstanceType<typeof MongoConfigSpec>>();
  const mongoConfigSpec = ref<ClusterSpecModel & {
    shard_node_num: number;
    shard_num: number;
    shard_node_spec: string;
    machine_num: number;
    count: number;
  } | null>(null);
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
        validator: (val: string) => nameRegx.test(val),
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
    const capacity = mongoConfigSpec.value?.capacity || 0;

    return Math.round(capacity * (capacityPercentage / 100));
  });

  const {
    data: versionList,
    loading: getVersionsLoading,
  } = useRequest(getVersions, {
    defaultParams: [{ query_key: DBTypes.MONGODB }],
  });

  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
  };

  const handleChangeCloud = (info: {
    id: number | string,
    name: string
  }) => {
    cloudInfo.value = info;
  };

  const handleMongoConfigSpecChange = (value: typeof mongoConfigSpec.value) => {
    mongoConfigSpec.value = value;
  };

  const handleResetformData = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, initData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };

  const handleSubmit = async () => {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const { details } = formData;
    const {
      disaster_tolerance_level: disasterTolerenceLevel,
      resource_spec: resourceSpec,
    } = details;
    const {
      mongo_config: mongoConfig,
      mongodb,
      mongos,
    } = resourceSpec;
    const { cityName } = regionItemRef.value!.getValue();
    const mongoConfigSpecData = mongoConfigSpec.value as NonNullable<typeof mongoConfigSpec.value>;

    const params = {
      ...formData,
      details: {
        ...details,
        shard_machine_group: mongoConfigSpecData.machine_pair,
        shard_num: mongoConfigSpecData.shard_node_num * mongoConfigSpecData.shard_num,
        resource_spec: {
          mongo_config: {
            spec_id: mongoConfig.spec_id,
            count: mongoConfig.count,
            affinity: disasterTolerenceLevel,
            location_spec: {
              city: cityName,
              sub_zone_ids: [],
            },
            ...mongoCofigSpecRef.value!.getData(),
          },
          mongodb: {
            ...mongodb,
            affinity: cityName,
            location_spec: {
              city: disasterTolerenceLevel,
              sub_zone_ids: [],
            },
            count: mongoConfigSpecData.machine_pair * 3, // shard_machine_group * 3(固定值)
            ...mongosSpecRef.value!.getData(),
          },
          mongos: {
            ...mongos,
            affinity: disasterTolerenceLevel,
            location_spec: {
              city: cityName,
              sub_zone_ids: [],
            },
            spec_name: mongoConfigSpecData.spec_name,
            cpu: mongoConfigSpecData.cpu,
            mem: mongoConfigSpecData.mem,
            storage_spec: mongoConfigSpecData.storage_spec,
            instance_num: mongoConfigSpecData.instance_num,
          },
        },
      },
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
  @import "@styles/applyInstance.less";

  .shared-cluster-apply {
    .input-desc {
      margin-left: 12px;
      font-size: 12px;
      color: #63656E;
    }


    :deep(.item-input) {
      width: 462px;
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
