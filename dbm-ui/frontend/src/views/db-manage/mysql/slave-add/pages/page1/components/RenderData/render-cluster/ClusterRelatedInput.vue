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
  <div class="cluster-infos">
    <div
      class="cluster-infos-current"
      @click="handleEdit">
      <span
        v-overflow-tips
        class="text-overflow">
        {{ data.domain }}
      </span>
      <DbIcon
        ref="iconRef"
        type="associated" />
    </div>
    <ul class="cluster-infos-related">
      <li
        v-for="item of data.checked_related"
        :key="item.id"
        v-overflow-tips
        class="text-overflow">
        {{ item.master_domain }}
      </li>
    </ul>
  </div>
  <div
    ref="relatedRef"
    class="related-clusters">
    <div class="related-clusters-title">
      <strong>{{ t('同机关联集群') }}</strong>
      <span>{{ t('同主机关联的其他集群_勾选后一同添加从库') }}</span>
    </div>
    <template v-if="data.cluster_related.length > 0">
      <BkCheckboxGroup
        :model-value="data.checked_related.map((item) => item.id)"
        @change="handleRelatedChange">
        <BkCheckbox
          v-for="item of data.cluster_related"
          :key="item.id"
          :label="item.id">
          {{ item.master_domain }}
        </BkCheckbox>
      </BkCheckboxGroup>
    </template>
    <p
      v-else
      style="font-size: 14px; color: #63656e">
      {{ t('无同机关联集群') }}
    </p>
  </div>
</template>

<script setup lang="ts">
  import type { Instance, SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { dbTippy } from '@common/tippy';

  export interface Props {
    data: {
      domain: string;
      id: number;
      cluster_related: TendbhaModel[];
      checked_related: TendbhaModel[];
    };
  }

  interface Emits {
    (e: 'change-related', values: number[]): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isEdit = defineModel<boolean>({
    default: true,
  });

  const { t } = useI18n();

  const inputRef = ref();
  const iconRef = ref();
  const relatedRef = ref();

  let tippyInst: Instance;

  watch(
    () => props.data,
    () => {
      isEdit.value = !props.data.id;
    },
    { immediate: true, deep: true },
  );

  watch(
    isEdit,
    (mode) => {
      setTimeout(() => {
        if (!mode) {
          tippyInst = dbTippy(iconRef.value.$el as SingleTarget, {
            content: relatedRef.value,
            placement: 'bottom-start',
            appendTo: () => document.body,
            theme: 'light',
            maxWidth: 'none',
            interactive: true,
            arrow: true,
            offset: [0, 8],
            zIndex: 999999,
            hideOnClick: true,
          });
        } else {
          tippyInstDestroy();
        }
      });
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    tippyInstDestroy();
  });

  const tippyInstDestroy = () => {
    if (tippyInst) {
      tippyInst.hide();
      tippyInst.unmount();
      tippyInst.destroy();
    }
  };

  const handleEdit = () => {
    isEdit.value = true;
    nextTick(() => {
      inputRef.value?.focus?.();
    });
  };

  const handleRelatedChange = (values: number[]) => {
    emits('change-related', values);
  };
</script>

<style lang="less" scoped>
  .cluster-infos {
    padding: 0 16px;

    .cluster-infos-current {
      display: flex;
      overflow: hidden;
      line-height: 42px;
      cursor: pointer;
      align-items: center;

      .db-icon-associated {
        width: 20px;
        height: 20px;
        margin-left: 4px;
        line-height: 20px;
        color: @primary-color;
        text-align: center;
        background-color: #e1ecff;
        border-radius: 2px;
        flex-shrink: 0;
      }
    }

    .cluster-infos-related {
      overflow: hidden;
      font-size: @font-size-mini;
      line-height: 22px;
      color: @gray-color;

      li {
        &:last-child {
          padding-bottom: 8px;
        }

        &::before {
          display: inline-block;
          width: 20px;
          height: 1px;
          margin-right: 12px;
          vertical-align: middle;
          background-color: #979ba5;
          content: '';
        }
      }
    }
  }

  .related-clusters {
    padding-top: 4px;

    .related-clusters-title {
      padding-bottom: 8px;

      strong {
        color: @title-color;
      }
    }

    .bk-checkbox {
      display: flex;
      padding-bottom: 8px;
      margin-left: 0;
      align-items: center;
    }
  }
</style>
