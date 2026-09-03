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
    :confirm-handler="handleDeleteVersion"
    :confirm-text="t('删除')"
    :content="t('删除操作无法撤回，请谨慎操作！')"
    :disabled="!permission || isAppliedInstance"
    placement="bottom"
    theme="danger"
    :title="t('确认删除该版本？')">
    <AuthButton
      v-bk-tooltips="{
        content: t('含有实例，无法删除'),
        disabled: !isAppliedInstance,
      }"
      action-id="package_manage"
      class="ml-12"
      :disabled="isAppliedInstance"
      :loading="deleteDbVersionLoading"
      :permission="permission"
      :resource="dbType"
      size="small"
      text
      theme="primary">
      {{ t('删除') }}
    </AuthButton>
  </DbPopconfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { deleteDbVersion } from '@services/source/version';

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

  const isAppliedInstance = computed(() => {
    const packages = props.data.packages;
    return Array.isArray(packages) && packages.some((item) => item.instances > 0);
  });

  const { loading: deleteDbVersionLoading, runAsync: runDeleteDbVersion } = useRequest(deleteDbVersion, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  // 返回 Promise 交给 DbPopconfirm，由它接管确认按钮 loading 与请求成功后的关闭
  const handleDeleteVersion = () =>
    runDeleteDbVersion({
      id: props.data.id,
    });
</script>
