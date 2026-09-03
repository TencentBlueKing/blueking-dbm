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
    :confirm-handler="handleDeleteRelease"
    :confirm-text="t('删除')"
    :content="t('删除操作无法撤回，请谨慎操作！')"
    :disabled="data?.isDeleteDisabled"
    placement="bottom"
    theme="danger"
    :title="t('确认删除该发行版？')">
    <AuthTemplate
      action-id="package_manage"
      :permission="data?.permission.package_manage"
      :resource="dbType">
      <DbIcon
        v-bk-tooltips="{
          content: data?.isDeleteDisabled
            ? t('该发行版下存在 n 个版本，请删除后再操作', { n: data.dbversion_count })
            : t('删除'),
          disabled: !data?.isDeleteDisabled,
        }"
        class="edit-icon"
        :class="{ 'is-disabled': data?.isDeleteDisabled }"
        type="delete"
        @click.stop />
    </AuthTemplate>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { deleteReleaseVersion } from '@services/source/version';

  import { messageSuccess } from '@utils';

  interface Props {
    data?: ReleaseVersionModel;
    dbType: string;
    pkgType: string;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { runAsync: runDeleteReleaseVersion } = useRequest(deleteReleaseVersion, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  // 返回 Promise 交给 DbPopconfirm，由它接管确认按钮 loading 与请求成功后的关闭
  const handleDeleteRelease = () =>
    runDeleteReleaseVersion({
      db_type: props.dbType,
      id: props.data!.id,
      pkg_type: props.pkgType,
    });
</script>
