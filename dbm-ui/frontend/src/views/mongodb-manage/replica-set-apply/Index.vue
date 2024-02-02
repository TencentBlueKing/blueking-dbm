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
        class="apply-form mb-16"
        :model="formData"
        :rules="rules">
        <DbCard :title="t('业务信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            @change-biz="handleChangeBiz" />
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
            <span class="input-desc">{{ t('默认从n开始分配', [formData.details.start_port]) }}</span>
          </BkFormItem>
        </DbCard>
        <DbCard :title="t('部署需求')">
          <BkFormItem
            :label="t('主从节点数')"
            property="details.node_count"
            required>
            <BkInput
              v-model="formData.details.node_count"
              clearable
              :max="11"
              :min="3"
              show-clear-only-hover
              :step="2"
              style="width: 185px;"
              type="number" />
          </BkFormItem>
          <BkFormItem
            :label="t('部署副本集数量')"
            property="details.replica_count"
            required>
            <BkInput
              v-model="formData.details.replica_count"
              clearable
              :min="1"
              show-clear-only-hover
              style="width: 185px;"
              type="number" />
          </BkFormItem>
          <BkFormItem
            :label="t('每台主机部署副本集数量')"
            property="details.node_replica_count"
            required>
            <BkInput
              v-model="formData.details.node_replica_count"
              clearable
              :min="1"
              show-clear-only-hover
              style="width: 185px;"
              type="number" />
          </BkFormItem>
          <BkFormItem
            class="service"
            :label="t('域名设置')"
            required>
            <DomainTable
              v-model:domains="formData.details.replica_sets"
              :app-abbr="formData.details.db_app_abbr"
              :nodes-number="formData.details.node_count" />
          </BkFormItem>
          <BkFormItem
            :label="t('后端存储规格')"
            property="details.resource_spec.spec_id"
            required>
            <SpecSelector
              ref="specRef"
              v-model="formData.details.resource_spec.spec_id"
              :biz-id="formData.bk_biz_id"
              :cloud-id="formData.details.bk_cloud_id"
              :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
              :machine-type="MachineTypes.MONGOS"
              style="width: 314px;" />
            <span class="input-desc ml-32">
              {{ t('共需n台', [hostNumber]) }} ,
              <BkPopover
                allow-html
                content="#calculate_rule_content"
                theme="light">
                <BkButton
                  text
                  theme="primary">
                  {{ t('计算规则') }}
                </BkButton>
              </BkPopover>
            </span>
            <div style="display: none;">
              <div id="calculate_rule_content">
                <span style="font-weight: bolder;">{{ t('所需主机数量') }}</span>
                = ( {{ t('部署副本集数量') }} / {{ t('每台主机部署副本集数量') }} ) * {{ t('主从节点数') }}
              </div>
            </div>
          </BkFormItem>
          <BkFormItem
            :label="t('每台主机oplog容量占比')"
            property="details.oplog_percent"
            required>
            <BkInput
              v-model="formData.details.oplog_percent"
              clearable
              :min="1"
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
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

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

  import AffinityItem from '@components/apply-items/AffinityItem.vue';
  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import DbForm from '@components/db-form/index.vue';

  import DomainTable from './components/DomainTable.vue';

  const initData = () => ({
    bk_biz_id: '' as number | '',
    ticket_type: TicketTypes.MONGODB_REPLICASET_APPLY,
    remark: '',
    details: {
      db_app_abbr: '',
      bk_cloud_id: 0,
      cluster_type: ClusterTypes.MONGO_REPLICA_SET,
      db_version: '',
      replica_sets: [] as Array<{
        set_id: string,
        domain: string,
        name: string,
      }>,
      start_port: 25501,
      node_count: 3,
      replica_count: 1,
      node_replica_count: 1,
      oplog_percent: 10,
      city_code: '',
      disaster_tolerance_level: 'NONE',
      ip_source: 'resource_pool',
      resource_spec: {
        spec_id: '',
        count: 2,
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
  const specRef = ref<InstanceType<typeof SpecSelector>>();
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });
  const formData = reactive(initData());

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const rules = {
    'details.node_count': [
      {
        message: t('节点数目前只支持xxx', ['3, 5, 7, 9, 11']),
        trigger: 'change',
        validator: (val: number) => [3, 5, 7, 9, 11].includes(val),
      },
    ],
  };

  const hostNumber = computed(() => {
    const {
      node_count: nodesNumber,
      replica_count: setNumber,
      node_replica_count: setNumberPerHost,
    } = formData.details;

    return setNumber / setNumberPerHost * nodesNumber;
  });

  const estimatedCapacity = computed(() => {
    const clusterCapacity = specRef.value?.getData().storage_spec?.[0].size || 0;
    const capacityPercentage = formData.details.oplog_percent;

    return Math.round(clusterCapacity * (capacityPercentage / 100));
  });

  const {
    data: versionList,
    loading: getVersionsLoading,
  } = useRequest(getVersions, {
    defaultParams: [{ query_key: DBTypes.MONGODB }],
  });

  // 设置 domain 数量
  watch(() => formData.details.replica_count, (count: number) => {
    if (count > 0 && count <= 200) {
      const len = formData.details.replica_sets.length;
      if (count > len) {
        const appends = Array.from({ length: count - len }, () => ({
          set_id: '',
          domain: '',
          name: '',
        }));
        formData.details.replica_sets.push(...appends);
        return;
      }
      if (count < len) {
        formData.details.replica_sets.splice(count, len - count);
        return;
      }
    }
  }, {
    immediate: true,
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

  const handleResetFormdata = () => {
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
    await formRef.value!.validate();

    baseState.isSubmitting = true;

    // const { cityName } = regionItemRef.value.getValue();
    const { details } = formData;
    const params = {
      ...formData,
      details: {
        ...details,
        spec_id: details.resource_spec.spec_id,
        resource_spec: {
          mongodb: {
            count: details.node_count,
            spec_id: details.resource_spec.spec_id,
            ...specRef.value!.getData(),
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

  .apply-instance {
    :deep(.item-input) {
      width: 462px;
    }

    .input-desc {
      margin-left: 12px;
      font-size: 12px;
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
