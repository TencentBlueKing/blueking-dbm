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
  <EditableColumn
    :label="t('规格需求')"
    :min-width="150">
    <template #head>
      <div v-bk-tooltips="t('默认使用部署方案中选定的规格，将从资源池自动匹配机器')">
        <span class="spec-title">{{ t('规格需求') }}</span>
      </div>
    </template>
    <div style="flex: 1">
      <EditableBlock
        v-model="localValue.name"
        :placeholder="t('自动生成')">
        <template #append>
          <SpecPanel
            v-if="localValue.id"
            :data="localValue"
            :hide-qps="!localValue.qps.min">
            <DbIcon
              class="visible-icon ml-4"
              type="visible1" />
          </SpecPanel>
        </template>
      </EditableBlock>
      <EditableBlock
        v-if="relatedSlaveSpec.id"
        v-model="relatedSlaveSpec.name"
        class="related-cell"
        :placeholder="t('自动生成')">
        <template #append>
          <SpecPanel
            :data="relatedSlaveSpec"
            :hide-qps="!relatedSlaveSpec.qps.min">
            <DbIcon
              class="visible-icon ml-4"
              type="visible1" />
          </SpecPanel>
        </template>
      </EditableBlock>
    </div>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import SpecPanel from '@components/render-table/columns/spec-display/Panel.vue';

  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  const modelValue = defineModel<{
    related_slave?: {
      spec_config: SpecInfo;
    }; // 关联的从库ip，仅当role=redis_master时存在
    spec_config: SpecInfo;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const createDefaultData = () => ({
    count: 0,
    cpu: {
      max: 1,
      min: 0,
    },
    id: 0,
    mem: {
      max: 1,
      min: 0,
    },
    name: '',
    qps: {
      max: 1,
      min: 0,
    },
    storage_spec: [
      {
        mount_point: '/data',
        size: 0,
        type: '默认',
      },
    ],
  });

  const localValue = computed<SpecInfo>(() => Object.assign(createDefaultData(), modelValue.value.spec_config));

  const relatedSlaveSpec = computed<SpecInfo>(() =>
    Object.assign(createDefaultData(), modelValue.value.related_slave?.spec_config),
  );
</script>

<style lang="less" scoped>
  .spec-title {
    border-bottom: 1px dashed #979ba5;
  }

  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
