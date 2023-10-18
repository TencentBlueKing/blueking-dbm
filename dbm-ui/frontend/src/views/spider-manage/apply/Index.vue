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
  <div class="apply-instance">
    <DbForm
      ref="formRef"
      auto-label-width
      class="apply-form"
      :model="formdata"
      :rules="rules">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formdata.details.db_app_abbr"
          v-model:biz-id="formdata.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <ClusterName v-model="formdata.details.cluster_name" />
        <ClusterAlias
          v-model="formdata.details.cluster_alias"
          :biz-id="formdata.bk_biz_id"
          cluster-type="tendbcluster" />
        <CloudItem v-model="formdata.details.bk_cloud_id" />
      </DbCard>
      <DbCard :title="$t('部署需求')">
        <ModuleItem
          v-model="formdata.details.db_module_id"
          :biz-id="formdata.bk_biz_id" />
        <BkFormItem
          :label="$t('接入层Master')"
          required>
          <div class="resource-pool-item">
            <BkFormItem
              :label="$t('规格')"
              property="details.resource_spec.spider.spec_id"
              required>
              <SpecSelector
                ref="specProxyRef"
                v-model="formdata.details.resource_spec.spider.spec_id"
                :biz-id="formdata.bk_biz_id"
                :cloud-id="formdata.details.bk_cloud_id"
                cluster-type="tendbcluster"
                machine-type="spider" />
            </BkFormItem>
            <BkFormItem
              :label="$t('数量')"
              property="details.resource_spec.spider.count"
              required>
              <BkInput
                v-model="formdata.details.resource_spec.spider.count"
                :min="2"
                type="number" />
              <span class="input-desc">{{ $t('至少n台', {n: 2}) }}</span>
            </BkFormItem>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="$t('后端存储规格')"
          required>
          <BackendQPSSpec
            ref="specBackendRef"
            v-model="formdata.details.resource_spec.backend_group"
            :biz-id="formdata.bk_biz_id"
            :cloud-id="formdata.details.bk_cloud_id"
            cluster-type="tendbcluster"
            machine-type="remote" />
        </BkFormItem>
        <BkFormItem
          :label="$t('访问端口')"
          property="details.spider_port"
          required>
          <BkInput
            v-model="formdata.details.spider_port"
            clearable
            :max="65535"
            :min="25000"
            style="width: 185px;"
            type="number" />
          <span class="input-desc">
            {{ $t('范围min_max', {min: 25000, max: 65535}) }}
          </span>
        </BkFormItem>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="formdata.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px;"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
    <div class="absolute-footer">
      <BkButton
        :loading="baseState.isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <BkButton
        :disabled="baseState.isSubmitting"
        @click="handleResetFormdata">
        {{ $t('重置') }}
      </BkButton>
      <BkButton
        :disabled="baseState.isSubmitting"
        @click="handleCancel">
        {{ $t('取消') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types/common';

  import { useApplyBase, useInfo  } from '@hooks';

  import { nameRegx } from '@common/regex';

  import BackendQPSSpec from '@components/apply-items/BackendQPSSpec.vue';
  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';

  import ModuleItem from './components/ModuleItem.vue';

  const { t } = useI18n();

  const initData = () => ({
    bk_biz_id: '' as number | '',
    remark: '',
    ticket_type: 'TENDBCLUSTER_APPLY',
    details: {
      bk_cloud_id: 0,
      db_app_abbr: '',
      cluster_name: '',
      cluster_alias: '',
      db_module_id: '',
      cluster_shard_num: 0,
      remote_shard_num: 0,
      resource_spec: {
        spider: {
          spec_id: 0,
          count: 2,
        },
        backend_group: {
          spec_id: 0,
          count: 0,
          capacity: '',
          future_capacity: '',
        },
      },
      spider_port: 25000,
    },
  });

  // 基础设置
  const {
    baseState,
    bizState,
    handleCancel,
    handleCreateAppAbbr,
    handleCreateTicket,
  } = useApplyBase();

  const formRef = ref();
  const specProxyRef = ref();
  const specBackendRef = ref();
  const formdata = ref(initData());
  const rules = {
    'details.cluster_name': [{
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'blur',
      validator: (val: string) => nameRegx.test(val),
    }],
  };

  /**
   * 变更业务
   */
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
  };

  /** 重置表单 */
  const handleResetFormdata = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        formdata.value = initData();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };

  async function handleSubmit() {
    await formRef.value?.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const details: Record<string, any> = _.cloneDeep(formdata.value.details);

      // 集群容量需求不需要提交
      delete details.resource_spec.backend_group.capacity;
      delete details.resource_spec.backend_group.future_capacity;

      const specInfo = specBackendRef.value.getData();
      return {
        ...details,
        cluster_shard_num: Number(specInfo.cluster_shard_num),
        remote_shard_num: specInfo.cluster_shard_num / specInfo.machine_pair,
        resource_spec: {
          spider: {
            ...details.resource_spec.spider,
            ...specProxyRef.value.getData(),
            count: Number(details.resource_spec.spider.count),
          },
          backend_group: {
            ...details.resource_spec.backend_group,
            count: specInfo.machine_pair,
            spec_info: specInfo,
          },
        },
      };
    };
    const params = {
      ...formdata.value,
      details: getDetails(),
    };
    // 若业务没有英文名称则先创建业务英文名称再创建单据，反正直接创建单据
    bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
  }
</script>

<style lang="less" scoped>
  @import "@styles/applyInstance.less";

  .apply-instance {
    :deep(.item-input) {
      width: 462px;
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }

    :deep(.resource-pool-item) {
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
