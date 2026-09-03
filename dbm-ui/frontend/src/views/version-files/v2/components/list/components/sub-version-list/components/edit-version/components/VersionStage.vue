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
  <BkSelect
    v-model="localValue"
    @change="handleValueChange"
    @toggle="handleStageToggle">
    <template #trigger>
      <div
        class="version-stage-trigger"
        :class="{ 'is-active': isShowPanel }">
        <div class="display-main">
          <BkTag
            v-if="displayValue"
            :stop-propagation="false"
            :theme="displayValue?.theme">
            {{ displayValue?.label }}
          </BkTag>
          <span
            v-else
            class="placeholder">
            {{ t('请选择版本阶段') }}
          </span>
        </div>
        <div class="icon-main">
          <DbIcon
            class="trigger-icon"
            type="down-big" />
        </div>
      </div>
    </template>
    <BkOption
      v-for="stage in versionStageList"
      :key="stage.value"
      :label="stage.label"
      :value="stage.value">
      <BkTag
        :stop-propagation="false"
        :theme="stage.theme">
        {{ stage.label }}
      </BkTag>
    </BkOption>
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { versionStageList, versionStageMap } from '@views/version-files/v2/common';

  type Emits = (e: 'valueChange') => void;

  const emits = defineEmits<Emits>();

  const localValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const isShowPanel = ref(false);

  const displayValue = computed(() => versionStageMap[localValue.value]);

  const handleValueChange = () => {
    emits('valueChange');
  };

  const handleStageToggle = (isShow: boolean) => {
    isShowPanel.value = isShow;
  };
</script>
<style lang="less">
  .bk-form-item {
    &.is-error {
      .version-stage-trigger {
        border-color: #ea3636;
      }
    }
  }

  .version-stage-trigger {
    display: flex;
    width: 100%;
    height: 32px;
    padding-left: 8px;
    cursor: pointer;
    background: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    align-items: center;
    justify-content: space-between;

    &:hover {
      border-color: #979ba5;
    }

    &.is-active {
      border-color: #3a84ff;

      .icon-main {
        .trigger-icon {
          transform: rotate(180deg);
          transition: transform 0.4s;
        }
      }
    }

    .display-main {
      .placeholder {
        font-size: 12px;
        color: #c4c6cc;
      }
    }

    .icon-main {
      padding-right: 8px;
      font-size: 13px;
      color: #979ba5;

      .trigger-icon {
        display: inline-block;
      }
    }
  }
</style>
