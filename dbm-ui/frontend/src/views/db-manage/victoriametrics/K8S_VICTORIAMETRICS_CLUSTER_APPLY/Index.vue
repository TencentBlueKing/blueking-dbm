<template>
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <div class="victoriametrics-standard-apply">
      <DbForm
        ref="formRef"
        auto-label-width
        class="apply-form mb-16"
        :model="formData">
        <DbCard :title="t('业务信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="k8s_victoriametrics_apply"
            @change-biz="handleChangeBiz" />
          <ClusterName
            v-model="formData.details.cluster_name"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER"
            :db-app-abbr="formData.details.db_app_abbr" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER"
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
            addon-type="victoriametrics" />
          <DbFormItem :label="t('部署模式')">
            <BkRadioGroup
              v-model="topoName"
              type="card">
              <BkRadioButton
                label="cluster"
                style="flex: 0 0 100px">
                {{ t('标准集群') }}
              </BkRadioButton>
              <span class="input-desc ml-12">
                {{ t('vminsert + vmselect + vmstorage，创建时自动挂载写入、查询 CLB') }}
              </span>
            </BkRadioGroup>
          </DbFormItem>
          <AddonSpecPlan
            v-model:vminsert="formData.details.vminsert"
            v-model:vmselect="formData.details.vmselect"
            v-model:vmstorage="formData.details.vmstorage"
            addon-type="victoriametrics"
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

  import type { VictoriaMetrics } from '@services/model/ticket/ticket';
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

  import AddonSpecPlan, {
    getDefaultVminsertConfig,
    getDefaultVmselectConfig,
    getDefaultVmstorageConfig,
  } from './components/AddonSpecPlan.vue';

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
      cluster_type: ClusterTypes.K8S_VICTORIAMETRICS_CLUSTER,
      creator: '',
      db_app_abbr: '',
      db_version: '', // 小版本
      k8s_cluster_name: '',
      major_version: '', // 大版本
      remark: '',
      vminsert: [getDefaultVminsertConfig()],
      vmselect: [getDefaultVmselectConfig()],
      vmstorage: [getDefaultVmstorageConfig()],
    },
    remark: '',
    ticket_type: TicketTypes.K8S_VICTORIAMETRICS_CLUSTER_APPLY,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);
  const userProfile = useUserProfile();
  const bizStore = useGlobalBizs();

  useTicketDetail<VictoriaMetrics.StandardApply>(TicketTypes.K8S_VICTORIAMETRICS_CLUSTER_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      const [vminsertItem, vmselectItem, vmstorageItem] = details.component_list;

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
        vminsert: [
          {
            component_name: 'vminsert',
            replicas: vminsertItem.replicas,
            request_cpu: Number(vminsertItem.request_cpu),
            request_memory: Number(vminsertItem.request_memory.replace('Gi', '')),
          },
        ],
        vmselect: [
          {
            component_name: 'vmselect',
            replicas: vmselectItem.replicas,
            request_cpu: Number(vmselectItem.request_cpu),
            request_memory: Number(vmselectItem.request_memory.replace('Gi', '')),
          },
        ],
        vmstorage: [
          {
            component_name: 'vmstorage',
            replicas: vmstorageItem.replicas,
            request_cpu: Number(vmstorageItem.request_cpu),
            request_memory: Number(vmstorageItem.request_memory.replace('Gi', '')),
            storage: Number(vmstorageItem.storage.replace('Gi', '')),
          },
        ],
      });
    },
  });

  const formRef = ref<InstanceType<typeof DbForm>>();
  const topoName = ref('cluster');

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
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
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

      const { vminsert, vmselect, vmstorage } = details;
      const vminsertItem = vminsert![0];
      const vmselectItem = vmselect![0];
      const vmstorageItem = vmstorage![0];

      // 组件版本 = 小版本-大版本（协议要求，如 1.115.0-2.0.0）
      // const componentVersion = `${details.db_version}-${details.major_version}`;
      const componentVersion = details.db_version;

      Object.assign(details, {
        bk_biz_name: bizStore.getBizInfoById(Number(formData.bk_biz_id))?.name || '',
        component_list: [
          {
            ...vminsertItem,
            request_cpu: `${vminsertItem.request_cpu}`,
            request_memory: `${vminsertItem.request_memory}Gi`,
            version: componentVersion,
          },
          {
            ...vmselectItem,
            request_cpu: `${vmselectItem.request_cpu}`,
            request_memory: `${vmselectItem.request_memory}Gi`,
            version: componentVersion,
          },
          {
            ...vmstorageItem,
            request_cpu: `${vmstorageItem.request_cpu}`,
            request_memory: `${vmstorageItem.request_memory}Gi`,
            storage: `${vmstorageItem.storage}Gi`,
            version: componentVersion,
          },
        ],
        created_by: userProfile.username,
        creator: userProfile.username,
        remark: formData.remark,
      });

      delete details.apply_mode;
      delete details.vminsert;
      delete details.vmselect;
      delete details.vmstorage;

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

  .victoriametrics-standard-apply {
    .item-input {
      width: 435px;
    }

    .input-desc {
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
