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
  <tr>
    <td>
      <div class="version-file-name-container">
        <div
          v-overflow-tips
          class="text-overflow">
          {{ data.name }}
        </div>
        <div
          v-overflow-tips
          class="version-file-md5 text-overflow">
          {{ data.md5 }}
        </div>
      </div>
    </td>
    <td>
      <BkSelect
        v-model="permitOsType"
        :clearable="false"
        ext-cls="version-files-version-row-select"
        @change="() => emits('osTypeChange')">
        <BkOption
          v-for="osType in osTypeList"
          :key="osType.value"
          v-bk-tooltips="{
            content: t('该 OS 已被其它文件占用'),
            disabled: !occupiedOsVersions[osType.value]?.has('all'),
          }"
          :disabled="occupiedOsVersions[osType.value]?.has('all')"
          :label="osType.label"
          :value="osType.value" />
      </BkSelect>
    </td>
    <td>
      <BkSelect
        v-model="permitOs"
        all-option-id="all"
        class="version-permit-os-select"
        filterable
        multiple
        multiple-mode="tag"
        show-all
        @change="() => emits('osVersionChange')"
        @toggle="handleOsVersionToggle">
        <template #trigger>
          <div
            class="version-display-trigger"
            :class="{ 'is-active': isShowVersionPanel }">
            <div class="display-main">
              <template v-if="data.lockedOsList.length > 0 || permitOs.length > 0">
                <div
                  v-for="version in data.lockedOsList"
                  :key="version"
                  class="fixed-tag-main">
                  <div class="text-content">
                    <DbIcon
                      v-if="version === 'all'"
                      class="mr-4"
                      type="quanbu-xuanzhong" />
                    <span>{{ version === 'all' ? t('全部') : version }}</span>
                  </div>
                  <DbIcon
                    v-bk-tooltips="t('该版本已被应用，无法删除')"
                    class="close-icon"
                    type="close" />
                </div>
                <div
                  v-for="(version, index) in permitOs"
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
          v-for="version in osVersionList"
          :key="version.value"
          v-bk-tooltips="{
            content: t('该 OS 版本已被其它文件占用'),
            disabled: !occupiedOsVersions[permitOsType]?.has(version.value),
          }"
          :disabled="occupiedOsVersions[permitOsType]?.has(version.value)"
          :label="version.label"
          :value="version.value" />
      </BkSelect>
    </td>
    <td>
      <DbIcon
        v-bk-tooltips="{
          content: t('该版本已被应用，无法删除'),
          disabled: !isApplied,
        }"
        class="version-row-delete-icon"
        :class="{ 'is-disabled': isApplied }"
        type="delete"
        @click="handleDelete" />
    </td>
  </tr>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      /** 已被应用、不可移除的 OS 版本 */
      lockedOsList: string[];
      md5: string;
      name: string;
    };
    isApplied?: boolean;
    /** 已被其它文件占用的 OS 版本，key 为 OS 类型 */
    occupiedOsVersions: Record<string, Set<string>>;
    osTypeList: { label: string; value: string }[];
    /** 当前 OS 类型下可选的 OS 版本 */
    osVersionList: { label: string; value: string }[];
  }

  interface Emits {
    (e: 'delete'): void;
    (e: 'osTypeChange'): void;
    (e: 'osVersionChange'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    isApplied: false,
  });

  const emits = defineEmits<Emits>();

  const permitOs = defineModel<string[]>('permitOs', {
    required: true,
  });
  const permitOsType = defineModel<string>('permitOsType', {
    required: true,
  });

  const { t } = useI18n();

  const isShowVersionPanel = ref(false);

  const handleDelete = () => {
    if (!props.isApplied) {
      emits('delete');
    }
  };

  const handleOsVersionToggle = (isShow: boolean) => {
    isShowVersionPanel.value = isShow;
  };

  const handleVersionDelete = (index: number) => {
    const latestValue = permitOs.value.slice();
    latestValue.splice(index, 1);
    permitOs.value = latestValue;
    emits('osVersionChange');
  };
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

  .version-file-name-container {
    width: 100%;
    overflow: hidden;

    .version-file-md5 {
      width: 100%;
      height: 18px;
      margin-top: -4px;
      margin-bottom: 10px;
      font-size: 12px;
      line-height: 18px;
      color: #c4c6cc;
    }
  }
</style>
