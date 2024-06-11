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
  <I18nT
    :keypath="keypath"
    style="font-size: 14px; color: #63656e"
    tag="span">
    <span style="font-weight: bold; color: #2dcb56"> {{ values[0] }} </span>
    <span style="font-weight: bold; color: #3a84ff"> {{ values[1] }} </span>
  </I18nT>
</template>

<script setup lang="ts">
  interface Props {
    keypath: string;
    values: [number, number];
  }

  defineProps<Props>();
</script>
