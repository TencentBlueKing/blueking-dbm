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
      <DbCard :title="t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          perrmision-action-id="riak_apply"
          @change-biz="handleChangeBiz" />
        <BkFormItem
          ref="moduleRef"
          class="is-required"
          :description="t('表示DB的用途')"
          :label="t('DB模块名')"
          property="details.db_module_id"
          required>
          <BkSelect
            v-model="formData.details.db_module_id"
            class="item-input"
            :clearable="false"
            filterable
            :input-search="false"
            :loading="getModulesLoading"
            :placeholder="t('请选择xx', [t('DB模块名')])">
            <AuthOption
              v-for="item in moduleList"
              :key="item.db_module_id"
              action-id="dbconfig_view"
              :biz-id="formData.bk_biz_id"
              :label="item.name"
              :name="item.name"
              :permission="item.permission.dbconfig_view"
              resource="riak"
              :value="item.db_module_id" />
          </BkSelect>
        </BkFormItem>
        <ClusterName v-model="formData.details.cluster_name" />
        <ClusterAlias
          v-model="formData.details.cluster_alias"
          :biz-id="formData.bk_biz_id"
          cluster-type="riak" />
        <CloudItem
          v-model="formData.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <RegionItem
        ref="regionItemRef"
        v-model="formData.details.city_code" />
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
            v-if="formData.details.ip_source === 'resource_pool'"
            class="mb-24">
            <BkFormItem
              :label="t('资源规格')"
              property="spec_id"
              required>
              <SpecSelector
                ref="specRef"
                v-model="formData.spec_id"
                :biz-id="formData.bk_biz_id"
                :cloud-id="formData.details.bk_cloud_id"
                :cluster-type="ClusterTypes.RIAK"
                machine-type="riak"
                style="width: 435px" />
            </BkFormItem>
            <BkFormItem
              :label="t('节点数量')"
              property="nodes_num"
              required>
              <BkInput
                v-model="formData.nodes_num"
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
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import type { BizItem, HostDetails } from '@services/types';

  import { useApplyBase, useInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  // 目前固定为此版本
  const dbVersionList = [2.2];

  const genDefaultFormData = () => ({
    bk_biz_id: '' as number | '',
    remark: '',
    ticket_type: TicketTypes.RIAK_CLUSTER_APPLY,
    spec_id: '' as number | '',
    nodes_num: 3,
    details: {
      bk_cloud_id: 0,
      db_app_abbr: '',
      ip_source: 'resource_pool',
      db_module_id: '' as number | '',
      cluster_name: '',
      cluster_alias: '',
      city_code: '',
      db_version: '2.2',
      nodes: [] as HostDetails[],
      // http_port: 8087,
    },
  });

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { baseState, bizState, handleCreateAppAbbr, handleCreateTicket, handleCancel } = useApplyBase();

  const formRef = ref();
  const specRef = ref();
  const nodesRef = ref();
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });
  const formData = reactive(genDefaultFormData());

  const {
    data: moduleList,
    run: getModulesRun,
    loading: getModulesLoading,
  } = useRequest(getModules, {
    manual: true,
  });

  watch(
    () => formData.bk_biz_id,
    (value) => {
      if (value) {
        formData.details.db_module_id = '';
        fetchModules(value);
      }
    },
  );

  const formRules = {
    nodes_num: [
      {
        validator: (value: number) => value >= 3,
        message: t('节点数至少为n台', [3]),
        trigger: 'change',
      },
    ],
    'details.nodes': [
      {
        validator: (value: HostDetails[]) => value.length >= 3,
        message: t('节点数至少为n台', [3]),
        trigger: 'change',
      },
    ],
  };

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  // 切换业务，需要重置 IP 相关的选择
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
  };

  const fetchModules = (bizId: number | null) => {
    if (!bizId) {
      return;
    }

    getModulesRun({
      bk_biz_id: bizId,
      cluster_type: ClusterTypes.RIAK,
    });
  };

  const handleChangeCloud = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;

    formData.details.nodes = [];
  };

  const disableHostSubmitMethods = (hostList: Array<HostDetails[]>) =>
    hostList.length < 3 ? t('至少n台', { n: 3 }) : false;

  const handleProxyIpChange = (data: HostDetails[]) => {
    formData.details.nodes = data;
    if (formData.details.nodes.length > 0) {
      nodesRef.value.clearValidate();
    }
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
      baseState.isSubmitting = true;

      const { db_module_id: moduleId } = formData.details;
      const moduleListValue = moduleList.value || [];
      const moduleIndex = moduleListValue.findIndex((moduleItem) => Number(moduleItem.db_module_id) === moduleId);

      const params = {
        ...formData,
        details: {
          ...formData.details,
          db_module_name: moduleListValue[moduleIndex].name,
        },
      };

      if (formData.details.ip_source === 'resource_pool') {
        Object.assign(params.details, {
          resource_spec: {
            riak: {
              count: formData.nodes_num,
              spec_id: formData.spec_id,
              ...specRef.value.getData(),
            },
          },
        });
      } else {
        Object.assign(params.details, {
          nodes: {
            riak: formData.details.nodes.map((nodeItem) => ({
              ip: nodeItem.ip,
              bk_host_id: nodeItem.host_id,
              bk_cloud_id: nodeItem.cloud_id,
            })),
          },
        });
      }

      // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
      bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
    });
  };

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
