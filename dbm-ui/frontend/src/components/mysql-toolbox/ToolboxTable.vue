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
  <DbForm
    ref="formRef"
    :model="data">
    <DbOriginalTable
      v-bind="$attrs"
      :border="['col', 'outer']"
      class="mysql-toolbox-table"
      :columns="renderColumns"
      :data="data"
      :show-overflow-tooltip="false" />
  </DbForm>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { TableProps } from '@/types/bkui-vue';

  interface Emits {
    (e: 'add', value: number): void,
    (e: 'remove', value: number): void,
  }

  interface Props {
    columns: TableProps['columns'],
    data: TableProps['data']
  }

  const props = withDefaults(defineProps<Props>(), {
    columns: () => [],
    data: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const formRef = ref();

  const renderColumns = computed(() => [
    ...props.columns,
    {
      label: t('操作'),
      width: 120,
      field: 'operations',
      render: ({ index }: { index: number }) => (
        <div class="opertaions">
          <bk-button
            text
            onClick={() => emits('add', index)}>
            <db-icon type="plus-fill" />
          </bk-button>
          <bk-button
            text
            disabled={props.data.length === 1}
            onClick={() => emits('remove', index)}>
            <db-icon type="minus-fill" />
          </bk-button>
        </div>
      ),
    },
  ]);

  defineExpose({
    validate: () => formRef.value.validate(),
  });
</script>

<style lang="less" scoped>
  .mysql-toolbox-table {
    border-top: 1px solid @disable-color;

    :deep(.bk-table-head) {
      .db-icon-batch-host-select {
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;

        &:hover {
          color: #1768ef;
        }
      }

      .column-required {
        position: relative;
        display: inline-block;
        padding-right: 8px;

        &::after {
          position: absolute;
          top: 4px;
          right: 0;
          line-height: auto;
          color: @danger-color;
          content: '*';
        }
      }
    }

    :deep(.bk-table-body) {
      .opertaions {
        .bk-button {
          margin-left: 18px;
          font-size: @font-size-normal;

          &:not(.is-disabled) i {
            color: @light-gray;

            &:hover {
              color: @gray-color;
            }
          }

          &.is-disabled {
            i {
              color: @disable-color;
            }
          }
        }
      }

      .cell {
        padding: 0 !important;

        .placeholder {
          padding: 0 12px;
          color: @disable-color;
          background-color: white;
          user-select: none;
        }

        .bk-form-label {
          display: none;
        }

        .bk-form-content {
          margin-left: 0 !important;
        }

        .bk-form-error-tips {
          top: 12px;
        }

        .bk-input {
          height: 42px;
        }

        .bk-tag-input .bk-tag-input-trigger {
          min-height: 42px;

          .placeholder {
            padding-left: 0;
            line-height: 40px;
          }
        }

        .bk-input:not(.is-focused),
        .bk-tag-input .bk-tag-input-trigger:not(.active),
        .bk-textarea:not(.is-focused),
        .bk-select-input,
        .bk-select-tag,
        .db-textarea-display {
          border-color: transparent;
        }

        .bk-select {
          .angle-up {
            display: none;
          }

          &:hover {
            .angle-up {
              display: flex;
            }
          }

          .bk-select-tag,
          .bk-select-trigger {
            min-height: 42px;
          }
        }

        .bk-form-item.is-error {
          .bk-input--text,
          .bk-textarea textarea,
          .bk-tag-input .bk-tag-input-trigger:not(.active),
          .bk-tag-input .bk-tag-input-trigger:not(.active) .placeholder,
          .bk-select-tag,
          .db-textarea-display {
            background-color: #fff0f1;
          }

          .bk-input:not(.is-focused),
          .bk-tag-input .bk-tag-input-trigger:not(.active),
          .bk-textarea:not(.is-focused),
          .bk-select-input,
          .bk-select-tag {
            border-color: #fff0f1;
          }
        }

        .bk-tag-input-trigger.disabled {
          .placeholder {
            background-color: #fafbfd;
          }
        }

        .bk-input:not(.is-disabled):hover,
        .bk-tag-input .bk-tag-input-trigger:not(.disabled):hover,
        .bk-textarea:hover,
        .bk-select-input:hover,
        .bk-select-tag:not(.is-disabled):hover,
        .db-textarea-display:hover {
          border-color: @border-primary;
        }
      }
    }
  }
</style>
