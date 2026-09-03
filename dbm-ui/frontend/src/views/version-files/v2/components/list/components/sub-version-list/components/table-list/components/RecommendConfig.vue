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
  <AuthTemplate
    action-id="package_manage"
    :permission="permission"
    :resource="dbType">
    <DbIcon
      v-bk-tooltips="{ content: toolTipContent }"
      class="set-recommended mr-6"
      :class="[{ 'is-recommended': data.recommend, 'is-disabled': !data.enable }]"
      :type="data.recommend ? 'star-fill' : 'star'"
      @click="handleSetRecommended" />
  </AuthTemplate>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

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

  const toolTipContent = computed(() => {
    if (!props.data.enable) {
      return t('未启用的版本无法设置');
    }

    if (props.data.recommend) {
      return t('当前推荐版本，点击取消');
    }

    return t('设为推荐版本');
  });

  const { run: runUpdateDbVersion } = useRequest(updateDbVersion, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const handleSetRecommended = () => {
    if (!props.data.enable) {
      return;
    }

    runUpdateDbVersion({
      id: props.data!.id,
      phase: props.data!.phase,
      recommend: !props.data.recommend,
    });
  };
</script>
