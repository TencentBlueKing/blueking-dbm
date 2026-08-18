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
  <BkButton
    v-if="!noPermission"
    :disabled="disabled"
    text
    @click="handleClick">
    <slot />
  </BkButton>
  <BkButton
    v-else
    v-cursor
    class="auth-button-disable"
    :disabled="false"
    text
    @click.stop="handleNoPermissionClick">
    <slot />
  </BkButton>
</template>

<script setup lang="ts">
  import { getApplyDataLink } from '@services/source/iam';

  import { permissionDialog } from '@utils';

  interface Props {
    actionId: string;
    disabled?: boolean;
    noPermission: boolean;
    resources: { id: number; type: string }[];
  }

  type Emits = (e: 'click') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const handleClick = () => {
    emits('click');
  };

  const handleNoPermissionClick = async () => {
    const applyData = await getApplyDataLink({
      action_ids: [props.actionId],
      resources: props.resources,
    });
    permissionDialog(applyData);
  };
</script>

<style lang="less">
  .auth-button-disable {
    color: #c4c6cc !important;
    background: #fafbfd !important;
    border-color: #dcdee5 !important;
    user-select: none !important;

    &.bk-button-primary {
      background-color: #dcdee5 !important;

      .bk-button-text {
        color: #fff !important;
      }
    }

    &.is-text {
      background-color: transparent !important;
      border-color: transparent !important;

      .bk-button-text,
      * {
        color: #c4c6cc !important;
      }
    }
  }
</style>
