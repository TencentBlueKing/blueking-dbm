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
    <div class="surrealdb-single-apply">
      <DbForm
        ref="formRef"
        auto-label-width
        class="apply-form mb-16"
        :model="formData">
        <DbCard :title="t('业务信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="k8s_surrealdb_apply"
            @change-biz="handleChangeBiz" />
          <ClusterName
            v-model="formData.details.cluster_name"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
            :db-app-abbr="formData.details.db_app_abbr" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.K8S_SURREALDB_SINGLE"
            required />
        </DbCard>
        <DbCard :title="t('部署环境')">
          <K8SApplyMode v-model="formData.details.apply_mode" />
          <K8SCityCode v-model="formData.details.city_code" />
          <K8SClusterName
            v-model="formData.details.k8s_cluster_name"
            :region-code="formData.details.city_code" />
        </DbCard>
        <DbCard :title="t('资源配置')">
          <K8SVersion
            v-model="formData.details.db_version"
            v-model:major-version="formData.details.major_version"
            addon-type="surrealdb" />
          <DbFormItem :label="t('部署模式')">
            <BkRadioGroup
              v-model="topoName"
              style="width: 270px"
              type="card">
              <BkRadioButton label="single">
                {{ t('单节点') }}
              </BkRadioButton>
              <span class="input-desc ml-12">{{ t('仅 surreal 单节点 + 嵌入式存储') }}</span>
            </BkRadioGroup>
          </DbFormItem>
          <AddonSpecPlan
            v-model:surreal="formData.details.surreal"
            addon-type="surrealdb"
            :addon-version="formData.details.major_version" />
          <DbFormItem :label="t('备注')">
            <BkInput
              v-model="formData.remark"
              :maxlength="100"
              :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
              style="width: 655px"
              type="textarea" />
          </DbFormItem>
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
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { SurrealDB } from '@services/model/ticket/ticket';
  import { getCloudList } from '@services/source/ipchooser';
  import type { BizItem } from '@services/types';

  import { useApplyBase, useTicketDetail } from '@hooks';

  import { useGlobalBizs, useUserProfile } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import K8SApplyMode from '@views/db-manage/common/apply-items/K8SApplyMode.vue';
  import K8SCityCode from '@views/db-manage/common/apply-items/K8SCityCode.vue';
  import K8SClusterName from '@views/db-manage/common/apply-items/K8SClusterName.vue';
  import K8SVersion from '@views/db-manage/common/apply-items/K8SVersion.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import AddonSpecPlan, { getDefaultSurrealConfig } from './components/AddonSpecPlan.vue';

  const initData = () => ({
    bk_biz_id: '' as number | '',
    details: {
      apply_mode: 'SharedMode', // 页面展示
      bk_biz_name: '',
      bk_cloud_id: '',
      bk_cloud_region: '',
      city_code: '',
      cluster_alias: '',
      cluster_name: '',
      cluster_type: ClusterTypes.K8S_SURREALDB_SINGLE,
      creator: '',
      db_app_abbr: '',
      db_version: '', // 小版本
      k8s_cluster_name: '',
      major_version: '', // 大版本
      remark: '',
      surreal: [getDefaultSurrealConfig()],
    },
    remark: '',
    ticket_type: TicketTypes.K8S_SURREALDB_SINGLE_APPLY,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { applyBizInfo, baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);
  const userProfile = useUserProfile();
  const bizStore = useGlobalBizs();

  useTicketDetail<SurrealDB.SingleApply>(TicketTypes.K8S_SURREALDB_SINGLE_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      const [surrealItem] = details.component_list;

      Object.assign(formData, {
        bk_biz_id: ticketDetail.bk_biz_id,
        remark: ticketDetail.remark,
      });
      Object.assign(formData.details, {
        city_code: details.city_code,
        cluster_alias: details.cluster_alias,
        cluster_name: details.cluster_name,
        db_app_abbr: details.db_app_abbr,
        db_version: details.db_version,
        k8s_cluster_name: details.k8s_cluster_name,
        major_version: details.major_version,
        surreal: [
          {
            component_name: 'surreal',
            replicas: surrealItem.replicas,
            request_cpu: Number(surrealItem.request_cpu),
            request_memory: Number(surrealItem.request_cpu.replace('Gi', '')),
            storage: Number(surrealItem.storage.replace('Gi', '')),
          },
        ],
      });
    },
  });

  const formRef = ref<InstanceType<typeof DbForm>>();
  const topoName = ref('single');

  const formData = reactive(initData());

  useRequest(getCloudList, {
    onSuccess(cloudList) {
      const cloudItem = cloudList.find((item) => item.bk_cloud_id === 0);
      if (cloudItem) {
        formData.details.bk_cloud_id = `${cloudItem.bk_cloud_id}`;
        formData.details.bk_cloud_region = cloudItem.bk_region;
      }
    },
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const handleChangeBiz = (info: BizItem) => {
    applyBizInfo(info);
    serviceApply?.changeBizId(info.bk_biz_id);
  };

  const handleResetFormdata = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, initData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
    });
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const { details }: { details: Partial<UnwrapRef<typeof formData>['details']> } = _.cloneDeep(formData);

      const { surreal } = details;
      const surrealItem = surreal![0];

      Object.assign(details, {
        bk_biz_name: bizStore.getBizInfoById(Number(formData.bk_biz_id))?.name || '',
        component_list: [
          {
            ...surrealItem,
            request_cpu: `${surrealItem.request_cpu}`,
            request_memory: `${surrealItem.request_memory}Gi`,
            storage: `${surrealItem.storage}Gi`,
          },
        ],
        creator: userProfile.username,
        remark: formData.remark,
      });

      delete details.apply_mode;
      delete details.surreal;

      return details;
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

  .surrealdb-single-apply {
    .item-input {
      width: 435px;
    }

    .input-desc {
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
