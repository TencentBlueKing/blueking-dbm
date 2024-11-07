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
  <BkDropdown
    v-bk-tooltips="{
      disabled: !disabled,
      content: t('请选择操作集群'),
    }"
    class="cluster-batch-operation"
    :disabled="disabled"
    @click.stop
    @hide="() => (isShowDropdown = false)"
    @show="() => (isShowDropdown = true)">
    <BkButton :disabled="disabled">
      {{ t('批量操作') }}
      <DbIcon
        class="cluster-batch-operation-icon ml-4"
        :class="[{ 'cluster-batch-operation-icon-active': isShowDropdown }]"
        type="up-big " />
    </BkButton>
    <template #content>
      <BkDropdownMenu class="cluster-batch-operation-popover">
        <BkDropdownItem
          v-for="item in list"
          :key="item.dbConsole"
          v-db-console="item.dbConsole"
          @click="item.click">
          <BkButton
            v-bk-tooltips="{
              disabled: !item.disabled,
              content: item.tooltips,
              placement: 'right',
            }"
            class="opration-button"
            :disabled="item.disabled"
            text>
            {{ item.text }}
          </BkButton>
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    disabled: boolean;
    list: {
      dbConsole: string;
      click: () => void;
      disabled: boolean;
      tooltips: string;
      text: string;
    }[];
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isShowDropdown = ref(false);
</script>

<style lang="less">
  .cluster-batch-operation-popover {
    .bk-dropdown-item {
      padding: 0;

      .opration-button {
        padding: 0 16px;
      }
    }
  }
</style>

<style lang="less" scoped>
  .cluster-batch-operation {
    .cluster-batch-operation-icon {
      transform: rotate(0);
      transition: all 0.2s;
    }

    .cluster-batch-operation-icon-active {
      transform: rotate(180deg);
    }
  }
</style>
