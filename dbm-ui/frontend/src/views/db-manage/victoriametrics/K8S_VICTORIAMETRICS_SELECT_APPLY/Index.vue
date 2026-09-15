<template>
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <div class="victoriametrics-select-apply">
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
            :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
            :db-app-abbr="formData.details.db_app_abbr" />
          <ClusterAlias
            v-model="formData.details.cluster_alias"
            :biz-id="formData.bk_biz_id"
            :cluster-type="ClusterTypes.K8S_VICTORIAMETRICS_SELECT"
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
                label="select"
                style="flex: 0 0 100px">
                {{ t('查询集群') }}
              </BkRadioButton>
              <span class="input-desc ml-12">{{ t('仅 vmselect，关联其他集群 vmstorage') }}</span>
            </BkRadioGroup>
          </DbFormItem>
          <AddonSpecPlan
            v-model:vmselect="formData.details.vmselect"
            addon-type="victoriametrics"
            :addon-version="formData.details.major_version" />
          <FormItemWithHint
            :label="t('Storage 节点')"
            property="details.storage_nodes"
            required
            :rules="storageNodesRules">
            <BkInput
              v-model="formData.details.storage_nodes"
              class="item-input"
              clearable
              :placeholder="t('多个节点请用逗号,分隔')" />
            <template #hint>
              {{ t('格式为 域名:端口，取来源标准集群基本信息「存储入口」的节点列表') }}
            </template>
          </FormItemWithHint>
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
  import { domainPort } from '@common/regex';

  import DbForm from '@components/db-form/index.vue';
  import FormItemWithHint from '@components/form-item-with-hint/Index.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import ClusterAlias from '@views/db-manage/common/apply-items/ClusterAlias.vue';
  import ClusterName from '@views/db-manage/common/apply-items/ClusterName.vue';
  import K8SApplyMode from '@views/db-manage/common/apply-items/K8SApplyMode.vue';
  import K8SCityCode from '@views/db-manage/common/apply-items/K8SCityCode.vue';
  import K8SClusterName from '@views/db-manage/common/apply-items/K8SClusterName.vue';
  import K8SVersion from '@views/db-manage/common/apply-items/K8SVersion.vue';
  import { serviceApplyKey } from '@views/service-apply/const.ts';

  import AddonSpecPlan, { getDefaultVmselectConfig } from './components/AddonSpecPlan.vue';

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
      cluster_type: ClusterTypes.K8S_VICTORIAMETRICS_SELECT,
      creator: '',
      db_app_abbr: '',
      db_version: '', // 小版本
      k8s_cluster_name: '',
      major_version: '', // 大版本
      remark: '',
      storage_nodes: '',
      vmselect: [getDefaultVmselectConfig()],
    },
    remark: '',
    ticket_type: TicketTypes.K8S_VICTORIAMETRICS_SELECT_APPLY,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();
  const serviceApply = inject(serviceApplyKey);
  const userProfile = useUserProfile();
  const bizStore = useGlobalBizs();

  // Storage 节点校验：多个节点用 , 分隔，逐段 trim 后均非空，且每段须为「域名:端口」或「IP:端口」
  const storageNodesRules = [
    {
      message: t('多个节点请用 , 分隔，且节点间不能为空'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return value.split(',').every((item) => item.trim().length > 0);
      },
    },
    {
      message: t('节点格式须为域名:端口'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return value.split(',').every((item) => domainPort.test(item.trim()));
      },
    },
  ];

  useTicketDetail<VictoriaMetrics.QueryApply>(TicketTypes.K8S_VICTORIAMETRICS_SELECT_APPLY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;

      const [vmselectItem] = details.component_list;

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
        storage_nodes: vmselectItem.env.EXTRA_ARGS.storageNode,
        vmselect: [
          {
            component_name: 'vmselect',
            replicas: vmselectItem.replicas,
            request_cpu: Number(vmselectItem.request_cpu),
            request_memory: Number(vmselectItem.request_memory.replace('Gi', '')),
          },
        ],
      });
    },
  });

  const formRef = ref<InstanceType<typeof DbForm>>();
  const topoName = ref('select');

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

      const { storage_nodes: storageNodes, vmselect } = details;
      const vmselectItem = vmselect![0];

      // 组件版本 = 小版本-大版本（协议要求，如 1.115.0-2.0.0）
      // const componentVersion = `${details.db_version}-${details.major_version}`;

      Object.assign(details, {
        bk_biz_name: bizStore.getBizInfoById(Number(formData.bk_biz_id))?.name || '',
        component_list: [
          {
            ...vmselectItem,
            env: {
              EXTRA_ARGS: {
                storageNode: storageNodes,
              },
            },
            request_cpu: `${vmselectItem.request_cpu}`,
            request_memory: `${vmselectItem.request_memory}Gi`,
            version: details.db_version,
          },
        ],
        created_by: userProfile.username,
        creator: userProfile.username,
        remark: formData.remark,
        // storage_nodes: storageNodes,
      });

      delete details.apply_mode;
      delete details.vmselect;
      delete details.storage_nodes;

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

  .victoriametrics-select-apply {
    .item-input {
      width: 435px;
    }

    .input-desc {
      font-size: 12px;
      color: #63656e;
    }
  }
</style>
