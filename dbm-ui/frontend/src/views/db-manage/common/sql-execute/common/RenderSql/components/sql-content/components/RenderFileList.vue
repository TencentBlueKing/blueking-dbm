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
  <div
    ref="rootRef"
    class="sql-execute-render-file-list"
    :style="styles">
    <div class="file-list-header">
      <span>{{ t('文件列表') }}</span>
      <span style="font-size: 12px; font-weight: normal; color: #979ba5">
        {{ t('按顺序执行') }}
      </span>
    </div>
    <div style="padding: 0 12px">
      <slot />
    </div>
    <ScrollFaker style="height: calc(100% - 110px)">
      <div class="file-list-wrapper">
        <Vuedraggable
          v-model="localList"
          item-key="id"
          @end="handleDragEnd">
          <template #item="{ element: fileItemData }">
            <div
              class="file-item"
              :class="{
                active: fileItemData.name === modelValue,
                'is-error':
                  fileData[fileItemData.name].isUploadFailed || fileData[fileItemData.name].grammarCheck?.isError,
              }"
              @click="handleClick(fileItemData.name)">
              <div
                v-overflow-tips
                class="file-item-text">
                {{ fileItemData.name }}
              </div>
              <div class="extend-box">
                <div
                  v-if="fileData[fileItemData.name].isUploading"
                  class="action-btn">
                  <div class="uploading-flag">
                    <DbIcon type="sync-pending" />
                  </div>
                </div>
                <template v-else>
                  <div class="upload-info">
                    <span
                      v-if="!fileData[fileItemData.name].grammarCheck"
                      style="color: #979ba5">
                      {{ t('待校验') }}
                    </span>
                    <DbIcon
                      v-else-if="fileData[fileItemData.name].grammarCheck?.isError"
                      style="color: #ea3636"
                      svg
                      type="attention-fill" />
                    <DbIcon
                      v-else-if="
                        fileData[fileItemData.name].isUploadFailed || fileData[fileItemData.name].isCheckFailded
                      "
                      style="color: #ea3636"
                      type="attention-fill" />
                    <DbIcon
                      v-else-if="fileData[fileItemData.name].isSuccess"
                      style="color: #2dcb56"
                      type="check-circle-fill" />
                  </div>
                  <div class="drag-flag">
                    <DbIcon
                      style="font-size: 14px; color: #fff"
                      type="drag" />
                  </div>
                  <div
                    v-bk-tooltips="t('移除')"
                    class="action-btn remove-btn"
                    @click.stop="handleRemove(fileItemData.name)">
                    <DbIcon
                      style="color: #fff"
                      type="delete" />
                  </div>
                </template>
              </div>
            </div>
          </template>
        </Vuedraggable>
      </div>
    </ScrollFaker>
  </div>
</template>
<script lang="ts">
  import Vuedraggable from 'vuedraggable';

  import type GrammarCheckModel from '@services/model/sql-import/grammar-check';

  export interface IFileData {
    isSuccess: boolean;
    isCheckFailded: boolean;
    isUploading: boolean;
    isUploadFailed: boolean;
    uploadErrorMessage: string;
    file: File | null;
    content: string;
    messageList: GrammarCheckModel['messageList'];
    grammarCheck?: GrammarCheckModel;
    realFilePath: string;
  }

  export const createFileData = (data = {} as Partial<IFileData>) => ({
    isSuccess: data.isSuccess || false,
    isCheckFailded: data.isCheckFailded || false,
    isUploading: data.isUploading || false,
    isUploadFailed: data.isUploadFailed || false,
    uploadErrorMessage: data.uploadErrorMessage || '',
    file: data.file || null,
    content: data.content || '',
    messageList: data.messageList || [],
    grammarCheck: data.grammarCheck,
    realFilePath: data.realFilePath || '',
  });
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { onMounted, ref, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    fileData: Record<string, IFileData>;
  }

  interface Emits {
    (e: 'remove', filename: string): void;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 选中的文件名
  const modelValue = defineModel<string>({
    required: true,
  });

  const filenameList = defineModel<string[]>('filenameList', {
    required: true,
  });

  const rootRef = ref<HTMLElement>();
  const styles = shallowRef({});
  const localList = ref<Array<Record<'id' | 'name', string>>>([]);

  watch(
    filenameList,
    () => {
      localList.value = filenameList.value.map((fileName) => ({
        id: fileName,
        name: fileName,
      }));
    },
    {
      immediate: true,
    },
  );

  const handleClick = (fileName: string) => {
    modelValue.value = fileName;
  };

  const handleDragEnd = () => {
    filenameList.value = localList.value.map((item) => item.name);
  };

  const handleRemove = (filename: string) => {
    modelValue.value = filename;
    const lastesfilenameList = [...filenameList.value];
    _.remove(lastesfilenameList, (item) => item === filename);
    filenameList.value = lastesfilenameList;
    emits('remove', filename);
  };

  onMounted(() => {
    const offsetTop = 145;
    styles.value = {
      height: `${window.innerHeight - offsetTop - 60}px`,
    };
  });
</script>
<style lang="less">
  @keyframes rotate-loading {
    0% {
      transform: rotateZ(0);
    }

    100% {
      transform: rotateZ(360deg);
    }
  }

  .sql-execute-render-file-list {
    height: 100%;
    background: #2e2e2e;
    border-right: 1px solid #3d3d40;

    .file-list-header {
      display: flex;
      height: 40px;
      padding: 0 16px;
      margin-bottom: 16px;
      font-weight: bold;
      line-height: 16px;
      color: #fff;
      align-items: center;
    }

    .file-list-wrapper {
      padding: 8px 12px;
      font-size: 12px;
      color: #c4c6cc;
      user-select: none;

      .file-item {
        display: flex;
        align-items: center;
        height: 36px;
        padding: 0 8px;
        cursor: pointer;
        background: rgb(255 255 255 / 8%);
        border-radius: 2px;

        &:hover {
          background: rgb(255 255 255 / 20%);

          .extend-box {
            .drag-flag,
            .remove-btn {
              display: flex;
            }

            .upload-info {
              display: none;
            }
          }
        }

        &.active {
          font-weight: bold;
          color: #fff;
          background: #1768ef;
          opacity: 100% !important;
        }

        &.is-error {
          color: rgb(255 86 86 / 100%);
          background: rgb(255 86 86 / 21%);
        }

        & ~ .file-item {
          margin-top: 8px;
        }

        .file-item-text {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .extend-box {
      display: flex;
      margin-left: auto;
      font-size: 12px;
      color: #c4c6cc;
      align-items: center;

      .drag-flag,
      .action-btn,
      .upload-info {
        display: flex;
        align-items: center;
      }

      .action-btn {
        width: 14px;
        padding-left: 4px;
      }

      .remove-btn,
      .drag-flag {
        display: none;
      }

      .drag-flag {
        padding-left: 4px;
      }

      .uploading-flag {
        color: #3a84ff;
        animation: rotate-loading 1s linear infinite;
      }

      .upload-info {
        padding-left: 4px;
      }
    }
  }
</style>
