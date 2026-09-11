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
  <DbPopconfirm
    :confirm-handler="handleConfirm"
    :disabled="!permission"
    :title="confirmTitle"
    :width="350"
    @toggle-show="handleToggleShow">
    <AuthSwitcher
      action-id="package_manage"
      :before-change="handleBeforeChange"
      :disabled="!permission"
      :model-value="localValue"
      :permission="permission"
      :resource="dbType"
      size="small"
      theme="primary" />
    <template #content>
      <template v-if="data.enable">
        <div>{{ t('停用后，新部署、升级等场景将无法选择该版本，故障替换按原版本替换不受影响。') }}</div>
        <div v-if="data.recommend">{{ t('注意：停用也将自动清除该版本的 “推荐” 标记') }}</div>
      </template>
      <span v-else>
        {{ t('确认后，该版本将加入可选版本列表，所有场景均可选择使用，如：部署、升级。') }}
      </span>
    </template>
  </DbPopconfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { updateDbVersion } from '@services/source/version';

  import { messageSuccess } from '@utils';

  interface Props {
    data: DbVersionModel;
    dbType: string;
    permission: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(false);
  // 请求进行中标记，用于区分「确认后关闭」和「未确认就关闭」两种关闭弹层的场景
  const isSubmitting = ref(false);

  const confirmTitle = computed(() =>
    props.data?.enable
      ? t('确认停用该版本（version）？', { version: props.data.name || '' })
      : t('确认启用该版本（version）？', { version: props.data.name || '' }),
  );

  // switcher 的 before-change 会一直等待，直到确认成功（resolve）或放弃（reject）
  let enableChangeResolver: ((value: boolean) => void) | undefined;
  let enableChangeRejecter: ((value: boolean) => void) | undefined;

  const releaseSwitcher = (isChanged: boolean) => {
    if (isChanged) {
      enableChangeResolver?.(true);
    } else {
      enableChangeRejecter?.(false);
    }
    enableChangeResolver = undefined;
    enableChangeRejecter = undefined;
  };

  watch(
    () => props.data,
    () => {
      localValue.value = props.data.enable;
    },
    {
      immediate: true,
    },
  );

  const handleBeforeChange = () => {
    return new Promise<boolean>((resolve, reject) => {
      if (!props.permission) {
        reject(false);
        return;
      }
      enableChangeResolver = resolve;
      enableChangeRejecter = reject;
    });
  };

  const handleConfirm = async () => {
    const nextValue = !localValue.value;
    isSubmitting.value = true;
    try {
      await updateDbVersion({
        enable: nextValue,
        id: props.data.id,
        phase: props.data.phase,
      });
    } catch {
      // 请求失败保持原开关状态，同时释放 switcher 的等待，避免它一直转圈
      releaseSwitcher(false);
      return;
    } finally {
      isSubmitting.value = false;
    }
    localValue.value = nextValue;
    releaseSwitcher(true);
    messageSuccess(t('操作成功'));
    emits('success');
  };

  const handleToggleShow = (isShow: boolean) => {
    // 确认流程自己会释放，这里只处理未确认就关掉气泡的情况
    if (isShow || isSubmitting.value) {
      return;
    }
    releaseSwitcher(false);
  };
</script>
