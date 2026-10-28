<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkDialog
    v-model:is-show="isShow"
    :width="640">
    <template #header>
      <div class="param-apply-title">
        <span>{{ t('应用设定值') }}</span>
        <DbTag>{{ t('已选n个参数', { n: selectedCount }) }}</DbTag>
      </div>
    </template>
    <TextOverflowLayout class="param-apply-cluster mb-16">
      {{ t('集群') }}：{{ cluster }}
    </TextOverflowLayout>
    <BkAlert
      v-if="skippedCount"
      class="mb-16"
      theme="info"
      :title="t('已自动过滤n个与运行值一致的参数', { n: skippedCount })" />
    <PrimaryTable
      :data="items"
      :max-height="472"
      row-key="conf_name">
      <TableColumn
        col-key="conf_name"
        ellipsis
        :min-width="200"
        :title="t('参数名')" />
      <TableColumn
        col-key="conf_value"
        :min-width="200"
        :title="t('设定值')">
        <template #default="{ row }: { row: ParameterConfigItem }">
          <TextOverflowLayout>
            {{ row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--') }}
          </TextOverflowLayout>
        </template>
      </TableColumn>
    </PrimaryTable>
    <template #footer>
      <BkButton
        v-bk-tooltips="t('后端协议待 PEER 确认')"
        class="mr-8"
        disabled
        style="min-width: 88px"
        theme="primary">
        {{ t('应用') }}
      </BkButton>
      <BkButton @click="isShow = false">{{ t('取消') }}</BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ParameterConfigItem } from '@services/source/configs';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    cluster: string;
    items: ParameterConfigItem[];
    selectedCount: number;
    skippedCount: number;
  }

  defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  // 待 PEER 确认：打开前以后台预检查替换页面快照，提交校验、任务创建及完成回读不可用前端模拟。
</script>

<style lang="less" scoped>
  .param-apply-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .param-apply-cluster {
    color: #63656e;
  }
</style>
