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
    :width="680">
    <template #header>
      <div class="param-apply-title">
        <span>{{ t('确认应用设定值') }}</span>
        <DbTag>{{ t('全量n个参数', { n: items.length }) }}</DbTag>
      </div>
    </template>
    <TextOverflowLayout class="param-apply-cluster mb-16">
      {{ t('集群') }}：{{ cluster }}
    </TextOverflowLayout>
    <BkAlert
      class="mb-16"
      theme="info"
      :title="t('本次将应用当前 Tab 全部参数的设定值。')" />
    <template v-if="inconsistentItems.length">
      <div class="param-apply-preview-title mb-8">
        {{ t('运行值不一致的参数（n）', { n: inconsistentItems.length }) }}
      </div>
      <PrimaryTable
        :data="inconsistentItems"
        :max-height="200"
        row-key="conf_name">
        <TableColumn
          col-key="conf_name"
          ellipsis
          :min-width="200"
          :title="t('参数名')" />
        <TableColumn
          col-key="conf_value"
          :min-width="140"
          :title="t('设定值')">
          <template #default="{ row }: { row: ParameterConfigItem }">
            <TextOverflowLayout class="param-apply-value">
              {{ row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--') }}
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="runtime_value"
          :min-width="220"
          :title="t('运行值')">
          <template #default="{ row }: { row: ParameterConfigItem }">
            <RuntimeValue
              :encrypted="row.flag_encrypt === 1"
              readonly
              :runtime="runtimeConfigMap[row.conf_name]" />
          </template>
        </TableColumn>
      </PrimaryTable>
    </template>
    <p class="param-apply-note mt-8">
      {{
        inconsistentItems.length
          ? t('表格仅列出运行值不一致的参数。')
          : t('当前无运行值不一致的参数。')
      }}
    </p>
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

  import type { RuntimeConfig } from '@views/db-configure/components/runtime-config';
  import RuntimeValue from '@views/db-configure/components/RuntimeValue.vue';

  interface Props {
    cluster: string;
    items: ParameterConfigItem[];
    runtimeConfigMap: Record<string, RuntimeConfig>;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const inconsistentItems = computed(() =>
    props.items.filter((item) => props.runtimeConfigMap[item.conf_name]?.comparison === 'inconsistent'),
  );
  // 待 PEER 确认：以后台预检查替换全量快照，接入提交校验、任务创建及完成回读。
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

  .param-apply-preview-title {
    font-size: 12px;
    font-weight: 700;
    color: #313238;
  }

  .param-apply-value {
    color: #3a84ff;
  }

  .param-apply-note {
    font-size: 12px;
    line-height: 1.6;
    color: #979ba5;
  }
</style>
