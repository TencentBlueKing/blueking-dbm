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
  <BkDialog
    v-model:is-show="isShow"
    quick-close>
    <template #header>
      <div class="k8s-instance-list-vscaling-component-header">
        {{ t('升降配置') }}
        <div class="header-divider ml-8 mr-8" />
        <div class="header-role">{{ role }}</div>
      </div>
    </template>
    <div class="k8s-instance-list-vscaling-component mt-24">
      <DbForm
        ref="form"
        label-width="0"
        :model="formData">
        <DbFormItem
          property="cpu"
          required>
          <div class="form-box">
            <div class="box-label">CPU</div>
            <div class="box-count">{{ beforeData.cpu }} Core</div>
            <div class="box-arrow mr-24">
              <DbIcon type="arrow-right" />
            </div>
            <BkInput
              v-model="formData.cpu"
              :min="1"
              style="width: 200px"
              suffix="Core"
              type="number" />
          </div>
        </DbFormItem>
        <DbFormItem
          property="memory"
          required>
          <div class="form-box">
            <div class="box-label">{{ t('内存') }}</div>
            <div class="box-count">{{ beforeData.memory }} GB</div>
            <div class="box-arrow mr-24">
              <DbIcon type="arrow-right" />
            </div>
            <BkInput
              v-model="formData.memory"
              :min="1"
              style="width: 200px"
              suffix="GB"
              type="number" />
          </div>
        </DbFormItem>
      </DbForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="isSubmittingDisabled"
        :loading="isSubmittingLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmittingLoading"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SurrealdbHaInstanceModel from '@services/model/surrealdb/surrealdb-ha-instance';
  import { vscalingComponent } from '@services/source/kubernetesToolbox';

  import { useUserProfile } from '@stores';

  interface Props {
    clusterData: {
      cluster_name: string;
      k8s_cluster_name: string;
      namespace: string;
    };
    data: SurrealdbHaInstanceModel[];
    role: string;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const userProfile = useUserProfile();

  const formRef = useTemplateRef('form');

  const formData = ref({
    cpu: '' as number | '',
    memory: '' as number | '',
  });

  const beforeData = computed(() => {
    let cpu = 0;
    let memory = 0;

    if (props.data.length > 0) {
      const { resourceQuota } = props.data[0];
      cpu = resourceQuota.limitCpu;
      memory = resourceQuota.limitMemory;
    }

    return {
      cpu,
      memory,
    };
  });

  const isSubmittingDisabled = computed(() => {
    const { cpu: beforeCpu, memory: beforeMemory } = beforeData.value;
    const { cpu: afterCpu, memory: afterMemory } = formData.value;

    return !afterCpu || !afterMemory || (beforeCpu === afterCpu && beforeMemory === afterMemory);
  });

  const { loading: isSubmittingLoading, run: runVscalingComponent } = useRequest(vscalingComponent, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      emits('success');
    },
  });

  watch(isShow, () => {
    if (isShow.value) {
      formData.value = {
        cpu: '',
        memory: '',
      };

      formRef.value?.clearValidate();
    }
  });

  const handleConfirm = async () => {
    await formRef.value!.validate();

    const { cpu, memory } = formData.value;

    runVscalingComponent({
      bk_username: userProfile.username,
      clusterName: props.clusterData.cluster_name,
      componentList: [
        {
          componentName: props.role,
          limit: {
            cpu: Number(cpu),
            memory: `${memory}Gi`,
          },
          request: {
            cpu: Number(cpu),
            memory: `${memory}Gi`,
          },
        },
      ],
      k8sClusterName: props.clusterData.k8s_cluster_name,
      namespace: props.clusterData.namespace,
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .k8s-instance-list-vscaling-component-header {
    display: flex;
    align-items: center;

    .header-divider {
      width: 1px;
      height: 12px;
      background: #dcdee5;
    }

    .header-role {
      font-size: 14px;
      color: #979ba5;
    }
  }

  .k8s-instance-list-vscaling-component {
    .form-box {
      display: flex;
      padding: 8px;
      justify-content: space-between;
      align-items: center;
      background-color: #f5f7fa;

      .box-label {
        width: 60px;
        font-size: 14px;
        font-weight: bolder;
        color: #313238;
      }

      .box-count {
        width: 60px;
        font-size: 12px;
      }

      .box-arrow {
        width: 24px;
        height: 24px;
        font-size: 16px;
        line-height: 24px;
        color: #979ba5;
        text-align: center;
        background-color: #d8d8d8;
        border-radius: 999px;
      }
    }

    .bk-form-error {
      left: 224px;
    }
  }
</style>
