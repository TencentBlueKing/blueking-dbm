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
    :esc-close="false"
    :quick-close="false"
    :title="t('版本升级')"
    width="480">
    <template v-if="isShow">
      <BkForm
        form-type="vertical"
        :label-width="80"
        :model="formData">
        <BkFormItem :label="t('集群域名')">
          <div class="upgrade-domain">{{ clusterData.master_domain }}</div>
        </BkFormItem>
        <BkFormItem
          :label="t('当前版本')"
          property="currentVersion">
          <BkInput
            v-model="formData.currentVersion"
            disabled />
        </BkFormItem>
        <BkFormItem
          :label="t('目标版本')"
          property="newVersion"
          required>
          <BkSelect
            v-model="formData.newVersion"
            :loading="isVersionLoading"
            :placeholder="t('请选择目标版本')">
            <BkOption
              v-for="version in versionList"
              :key="version"
              :label="version"
              :value="version" />
          </BkSelect>
        </BkFormItem>
      </BkForm>
      <div class="upgrade-hint">
        {{ t('升级将对集群执行原地滚动升级_期间服务可能短暂受影响') }}
      </div>
    </template>
    <template #footer>
      <BkButton
        class="mr-8 w-88"
        :disabled="!formData.newVersion"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="ml-8 w-88"
        :disabled="isSubmitting"
        @click="isShow = false">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import { getDorisUpgradableVersions } from '@services/source/doris';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  interface Props {
    clusterData: DorisModel;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const formData = reactive({
    currentVersion: props.clusterData.major_version || '',
    newVersion: '',
  });

  const versionList = ref<string[]>([]);
  const isVersionLoading = ref(false);

  const fetchUpgradableVersions = () => {
    isVersionLoading.value = true;
    getDorisUpgradableVersions({ cluster_id: props.clusterData.id })
      .then((data) => {
        versionList.value = data || [];
        formData.newVersion = '';
      })
      .finally(() => {
        isVersionLoading.value = false;
      });
  };

  watch(
    isShow,
    () => {
      if (isShow.value) {
        Object.assign(formData, {
          currentVersion: props.clusterData.major_version || '',
          newVersion: '',
        });
        fetchUpgradableVersions();
      }
    },
    {
      immediate: true,
    },
  );

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_id: number;
    new_version: string;
  }>(TicketTypes.DORIS_UPGRADE, {
    onSuccess: () => {
      isShow.value = false;
      emits('change');
    },
  });

  const handleSubmit = async () => {
    if (!formData.newVersion) {
      return;
    }
    createTicketRun({
      details: {
        cluster_id: props.clusterData.id,
        new_version: formData.newVersion,
      },
    });
  };
</script>

<style scoped>
  .upgrade-domain {
    width: 100%;
    height: 32px;
    line-height: 32px;
    color: #313238;
    font-size: 13px;
    font-weight: 600;
    word-break: break-all;
  }

  .upgrade-hint {
    margin-top: 12px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }
</style>
