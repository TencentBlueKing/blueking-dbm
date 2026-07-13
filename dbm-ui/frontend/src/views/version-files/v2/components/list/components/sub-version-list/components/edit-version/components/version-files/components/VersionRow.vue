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
  <tr>
    <!-- 文件列 -->
    <td>
      <!-- 上传中状态 -->
      <template v-if="status === 'uploading'">
        <div class="version-file-name-container">
          <div class="version-file-name-row">
            <DbIcon
              class="file-icon"
              type="file" />
            <span
              v-overflow-tips
              class="text-overflow">
              {{ data.name }}
            </span>
          </div>
          <div class="file-upload-progress-wrapper">
            <div class="file-upload-progress">
              <div
                class="file-upload-progress-bar"
                :style="{ width: `${percentage}%` }" />
            </div>
            <span class="file-upload-progress-text">{{ t('上传中') }} {{ percentage }}%</span>
          </div>
        </div>
      </template>

      <!-- 已上传状态 -->
      <template v-else-if="status === 'staged'">
        <div class="version-file-name-container">
          <div
            v-overflow-tips
            class="text-overflow">
            {{ data.name }}
          </div>
          <div class="version-file-md5-staged">
            <DbIcon
              class="check-icon"
              type="check-circle-fill" />
            <span class="md5-text">MD5: {{ data.md5 }}</span>
          </div>
        </div>
      </template>

      <!-- 上传失败状态 -->
      <template v-else-if="status === 'failed'">
        <div class="version-file-name-container">
          <div class="version-file-name-row">
            <span
              v-overflow-tips
              class="text-overflow version-file-name-failed">
              {{ data.name }}
            </span>
          </div>
          <div class="version-file-err-msg">{{ errMsg || t('上传失败，请重试') }}</div>
        </div>
      </template>

      <!-- 无状态（编辑模式加载已有数据） -->
      <template v-else>
        <div class="version-file-name-container">
          <div
            v-overflow-tips
            class="text-overflow">
            {{ data.name }}
          </div>
          <div class="version-file-md5-staged">
            <DbIcon
              class="check-icon"
              type="check-circle-fill" />
            <span class="md5-text">MD5: {{ data.md5 }}</span>
          </div>
        </div>
      </template>
    </td>

    <!-- OS 选择列 - 仅在已上传状态显示 -->
    <td>
      <template v-if="status === 'staged' || status === undefined">
        <BkSelect
          v-model="localData.permit_os_type"
          :clearable="false"
          ext-cls="version-files-version-row-select"
          @change="(value: string) => handleOsTypeChange(value)">
          <BkOption
            v-for="system in systemList"
            :key="system.value"
            v-bk-tooltips="{
              content: t('该 OS 已被其它文件占用'),
              disabled: !(selectedAllSystems.has(system.value) && selectedAllVersions[system.value]?.has('all')),
            }"
            :disabled="selectedAllSystems.has(system.value) && selectedAllVersions[system.value]?.has('all')"
            :label="system.label"
            :value="system.value" />
        </BkSelect>
      </template>
      <span
        v-else
        class="cell-placeholder">--</span>
    </td>

    <!-- OS 版本选择列 - 仅在已上传状态显示 -->
    <td>
      <template v-if="status === 'staged' || status === undefined">
        <BkSelect
          v-model="localData.permit_os"
          all-option-id="all"
          class="version-permit-os-select"
          filterable
          multiple
          multiple-mode="tag"
          show-all
          @change="handleOsVersionChange"
          @toggle="handleOsVersionToggle">
          <template #trigger>
            <div
              class="version-display-trigger"
              :class="{ 'is-active': isShowVersionPanel }">
              <div class="display-main">
                <template v-if="existVersionList.length > 0 || localData.permit_os.length > 0">
                  <div
                    v-for="version in existVersionList"
                    :key="version"
                    class="fixed-tag-main">
                    <div class="text-content">{{ version }}</div>
                    <DbIcon
                      v-bk-tooltips="t('该版本已被应用，无法删除')"
                      class="close-icon"
                      type="close" />
                  </div>
                  <div
                    v-for="(version, index) in localData.permit_os"
                    :key="version"
                    class="closable-tag-main">
                    <div class="text-content">
                      <DbIcon
                        v-if="version === 'all'"
                        class="mr-4"
                        type="quanbu-xuanzhong" />
                      <span>{{ version === 'all' ? t('全部') : version }}</span>
                    </div>
                    <DbIcon
                      class="close-icon"
                      type="close"
                      @click.stop="handleVersionDelete(index)" />
                  </div>
                </template>
                <div
                  v-else
                  class="placeholder">
                  {{ t('请选择版本') }}
                </div>
              </div>
              <div class="icon-main">
                <DbIcon
                  class="trigger-icon"
                  type="down-big" />
              </div>
            </div>
          </template>
          <BkOption
            v-for="version in versionList"
            :key="version.value"
            v-bk-tooltips="{
              content: t('该 OS 版本已被其它文件占用'),
              disabled: !selectedAllVersions[localData.permit_os_type]?.has(version.value),
            }"
            :disabled="selectedAllVersions[localData.permit_os_type]?.has(version.value)"
            :label="version.label"
            :value="version.value" />
        </BkSelect>
      </template>
      <span
        v-else
        class="cell-placeholder">--</span>
    </td>

    <!-- 操作列 -->
    <td>
      <div class="version-row-actions">
        <!-- 上传中: 仅删除 -->
        <template v-if="status === 'uploading'">
          <BkButton
            text
            theme="danger"
            @click="handleDelete">
            {{ t('删除') }}
          </BkButton>
        </template>

        <!-- 已上传: 替换 + 删除 -->
        <template v-else-if="status === 'staged' || status === undefined">
          <BkButton
            text
            theme="primary"
            @click="handleReplace">
            {{ t('替换') }}
          </BkButton>
          <BkButton
            v-bk-tooltips="{
              content: t('该版本已被应用，无法删除'),
              disabled: !isApplied,
            }"
            :disabled="isApplied"
            text
            theme="danger"
            @click="handleDelete">
            {{ t('删除') }}
          </BkButton>
        </template>

        <!-- 失败: 重试 + 删除 -->
        <template v-else-if="status === 'failed'">
          <BkButton
            text
            theme="primary"
            @click="handleRetry">
            {{ t('重试') }}
          </BkButton>
          <BkButton
            text
            theme="danger"
            @click="handleDelete">
            {{ t('删除') }}
          </BkButton>
        </template>
      </div>
    </td>
  </tr>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listSupportSystems } from '@services/source/package';

  type RowStatus = 'uploading' | 'staged' | 'failed';

  interface Props {
    data: {
      id?: number;
      md5: string;
      name: string;
      path: string;
      permit_os?: string[];
      permit_os_type?: string;
      size: number;
      tempId?: string;
    };
    errMsg?: string;
    isApplied?: boolean;
    isOnlyOneFile: boolean;
    percentage: number;
    selectedSystems: Set<string>;
    selectedVersions: Record<string, Set<string>>;
    status?: RowStatus;
  }

  interface Emits {
    (e: 'delete'): void;
    (e: 'replace'): void;
    (e: 'retry'): void;
    (e: 'systemOsTypeChange', isInit: boolean): void;
    (e: 'systemOsVersionChange'): void;
  }

  interface Exposes {
    getSelectedSystem: () => string;
    getSelectedVersions: () => string[];
    getValue: () => Props['data'] & typeof localData.value;
  }

  const props = withDefaults(defineProps<Props>(), {
    errMsg: undefined,
    isApplied: false,
    percentage: 0,
    status: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localData = ref({
    permit_os: [] as string[],
    permit_os_type: '',
  });
  const isShowVersionPanel = ref(false);
  const existVersionList = ref<string[]>([]);
  const systemList = ref<{ label: string; value: string }[]>([]);
  const versionList = ref<typeof systemList.value>([]);
  const selectedAllSystems = ref<Set<string>>(new Set());
  const selectedAllVersions = ref<Record<string, Set<string>>>({});

  let supportSystems: Record<string, string[]> = {};

  useRequest(listSupportSystems, {
    onSuccess(data) {
      supportSystems = data;
      systemList.value = Object.keys(data).map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  watch(
    () => [props.data, systemList.value, props.isApplied],
    () => {
      if (props.data && props.isApplied && systemList.value.length > 0) {
        localData.value.permit_os = [];
        existVersionList.value = props.data.permit_os!.slice();
      } else {
        existVersionList.value = [];
      }

      if (props.data) {
        if (!props.data.permit_os) {
          localData.value.permit_os = [];
        } else {
          localData.value.permit_os = props.data.permit_os.length ? props.data.permit_os : ['all'];
        }
        localData.value.permit_os_type = props.data.permit_os_type || '';
        if (localData.value.permit_os_type) {
          setTimeout(() => {
            handleOsTypeChange(localData.value.permit_os_type, true);
          });
        }
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [props.selectedSystems, props.selectedVersions],
    () => {
      nextTick(() => {
        selectedAllSystems.value = props.selectedSystems;
        selectedAllVersions.value = props.selectedVersions;
        if (localData.value.permit_os.length > 0) {
          if (
            props.selectedVersions[localData.value.permit_os_type]?.has('all') &&
            !localData.value.permit_os.includes('all')
          ) {
            localData.value.permit_os_type = '';
            localData.value.permit_os = [];
            versionList.value = [];
            emits('systemOsTypeChange', true);
            return;
          }

          const localSelectedVersions = _.cloneDeep(props.selectedVersions);
          if (localSelectedVersions[localData.value.permit_os_type]?.size > 0) {
            localData.value.permit_os.forEach((item) => {
              localSelectedVersions[localData.value.permit_os_type].delete(item);
            });
          }
          selectedAllVersions.value = localSelectedVersions;
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleOsTypeChange = (value: string, isInit = false) => {
    nextTick(() => {
      emits('systemOsTypeChange', isInit);
    });
    if (existVersionList.value.length > 0) {
      const exisetVersionSet = new Set(existVersionList.value);
      versionList.value = supportSystems[value].reduce<{ label: string; value: string }[]>((result, item) => {
        if (!exisetVersionSet.has(item)) {
          result.push({
            label: item,
            value: item,
          });
        }
        return result;
      }, []);
      return;
    }
    versionList.value = supportSystems[value]?.map((item) => ({
      label: item,
      value: item,
    }));
    if (!isInit) {
      if (props.isOnlyOneFile) {
        localData.value.permit_os = ['all'];
        return;
      }
      localData.value.permit_os = [];
    }
  };

  const handleOsVersionChange = () => {
    emits('systemOsVersionChange');
    nextTick(() => {
      emits('systemOsTypeChange', false);
    });
  };

  const handleDelete = () => {
    emits('delete');
  };

  const handleReplace = () => {
    emits('replace');
  };

  const handleRetry = () => {
    emits('retry');
  };

  const handleOsVersionToggle = (isShow: boolean) => {
    isShowVersionPanel.value = isShow;
  };

  const handleVersionDelete = (index: number) => {
    localData.value.permit_os.splice(index, 1);
    nextTick(() => {
      emits('systemOsTypeChange', false);
    });
  };

  defineExpose<Exposes>({
    getSelectedSystem() {
      return localData.value.permit_os_type;
    },
    getSelectedVersions() {
      return [...localData.value.permit_os, ...existVersionList.value];
    },
    getValue() {
      return {
        ...props.data,
        ...localData.value,
        permit_os: [...localData.value.permit_os, ...existVersionList.value],
      };
    },
  });
</script>
<style lang="less">
  .version-display-trigger {
    display: flex;
    height: 32px;
    padding-left: 8px;
    cursor: pointer;
    background: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    align-items: center;

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

    &.is-disabled {
      cursor: not-allowed;
      background-color: #fafbfd;
      border-color: #dcdee5;
    }

    .display-main {
      flex: 1;
      display: flex;
      flex-wrap: wrap;
      padding: 4px 0;
      gap: 4px;

      .placeholder {
        height: 20px;
        font-size: 12px;
        line-height: 20px;
        color: #c4c6cc;
      }

      .fixed-tag-main,
      .closable-tag-main {
        display: flex;
        height: 22px;
        padding: 0 3px 0 8px;
        background: #f0f1f5;
        border-radius: 2px;
        align-items: center;

        .text-content {
          flex: 1;
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .close-icon {
          margin-left: 2px;
          font-size: 16px;
          color: #dcdee5;
          cursor: not-allowed;
        }
      }

      .closable-tag-main {
        .close-icon {
          color: #979ba5;
          cursor: pointer;
        }
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

  .version-file-name-container {
    width: 100%;
    overflow: hidden;

    .version-file-name-row {
      display: flex;
      align-items: center;
      gap: 4px;

      .file-icon {
        flex-shrink: 0;
        font-size: 14px;
        color: #3a84ff;
      }

      .version-file-name-failed {
        color: #ea3636 !important;
      }
    }

    .file-upload-progress-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
    }

    .file-upload-progress {
      width: 120px;
      height: 2px;
      background: #f0f1f5;
      border-radius: 1px;
      overflow: hidden;

      .file-upload-progress-bar {
        height: 100%;
        background: #3a84ff;
        border-radius: 1px;
        transition: width 0.3s ease;
      }
    }

    .file-upload-progress-text {
      font-size: 12px;
      color: #3a84ff;
      white-space: nowrap;
    }

    .version-file-md5-staged {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 4px;

      .check-icon {
        flex-shrink: 0;
        font-size: 14px;
        color: #2dcb56;
      }

      .md5-text {
        font-family: monospace;
        font-size: 12px;
        color: #c4c6cc;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .version-file-err-msg {
      margin-top: 4px;
      font-size: 12px;
      color: #ea3636;
    }
  }

  .version-row-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .cell-placeholder {
    color: #c4c6cc;
    font-size: 12px;
  }

  .version-row-delete-icon {
    font-size: 13px;
    color: #979ba5;
    cursor: pointer;

    &.is-disabled {
      color: #c4c6cc;
      cursor: not-allowed;
    }
  }

  .bk-form-item {
    &.is-error {
      .version-display-trigger {
        border-color: #ea3636;
      }
    }
  }

  .version-files-version-row-select {
    z-index: 99999;
  }
</style>
