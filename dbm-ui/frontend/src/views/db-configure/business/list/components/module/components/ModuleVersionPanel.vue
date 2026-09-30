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
    v-if="layerList.length > 0"
    class="module-version-panel">
    <div
      v-for="layer in layerList"
      :key="layer.componentName"
      class="version-layer-row">
      <span class="layer-name">{{ layer.label }}</span>
      <span class="layer-version">
        <span class="layer-field-label">{{ t('版本') }}：</span>{{ layer.versionText }}
      </span>
      <div class="layer-os-actions">
        <span class="layer-os">
          <span class="layer-field-label">{{ t('操作系统版本') }}：</span>
          <span :class="{ 'os-empty': layer.osText === '--' }">{{ layer.osText }}</span>
          <!-- 跟随版本包：默认灰底标签；指定范围：橙色标签 -->
          <DbTag
            v-if="layer.info"
            class="ml-8"
            :theme="layer.info.follow_package ? '' : 'warning'">
            {{ layer.info.follow_package ? t('跟随版本包') : t('指定版本包') }}
          </DbTag>
        </span>
        <!-- 协议 §2：只能修改已经设置过版本的组件；存量模块该层没有版本时禁止编辑 -->
        <AuthButton
          v-bk-tooltips="layer.info ? t('编辑操作系统版本') : t('该层未设置版本，无法修改操作系统约束')"
          action-id="dbconfig_edit"
          class="layer-edit"
          :disabled="!layer.info"
          :resource="dbType"
          text
          @click="handleEditOs(layer)">
          <DbIcon type="bk-dbm-icon db-icon-edit" />
        </AuthButton>
      </div>
    </div>

    <!-- OS 编辑弹窗：一次只改一层；模式与取值按 §2.3 -->
    <BkDialog
      :is-show="isShowOsDialog"
      :title="t('编辑操作系统版本')"
      :width="560"
      @closed="handleDialogClosed">
      <div
        v-if="editingLayer"
        class="os-edit-body">
        <BkForm
          form-type="vertical"
          :model="dialogForm">
          <BkFormItem
            :label="t('操作系统版本')"
            required>
            <BkRadioGroup v-model="dialogForm.osMode">
              <BkRadio label="follow">
                {{ t('跟随版本包') }}<span class="radio-desc">（{{ t('随版本包自动更新') }}）</span>
              </BkRadio>
              <BkRadio label="specify">
                {{ t('指定范围') }}<span class="radio-desc">（{{ t('从版本包中勾选') }}）</span>
              </BkRadio>
            </BkRadioGroup>
            <VersionOsSelect
              v-model="dialogForm.specifyOs"
              class="os-specify-select"
              :mode="dialogForm.osMode"
              :version-id="editingLayer.info?.db_version_id ?? ''"
              @change="handleSpecifyChange" />
            <p
              v-if="dialogForm.osMode === 'specify' && specifyError"
              class="specify-error">
              {{ specifyError }}
            </p>
          </BkFormItem>
        </BkForm>
      </div>
      <template #footer>
        <BkButton
          :loading="isSubmitting"
          style="margin-right: 8px"
          theme="primary"
          @click="handleSaveOs">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          :disabled="isSubmitting"
          @click="handleDialogClosed">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { type ComponentVersionInfo, updateModuleVersionOs } from '@services/source/cmdb';

  import type { ClusterTypes, DBTypes } from '@common/const';

  import AuthButton from '@components/auth-component/button.vue';

  import VersionOsSelect from '@views/db-configure/components/VersionOsSelect.vue';

  import { messageSuccess } from '@utils';

  /**
   * 模块详情：按层展示版本与 OS，每层 OS 可编辑（创建后仅 OS 可改）
   */
  interface LayerDisplay {
    /** 协议组件名（backend/proxy 等） */
    componentName: string;
    /** 协议展示信息（存量模块可能缺失） */
    info?: ComponentVersionInfo;
    /** 展示名（存储层/接入层） */
    label: string;
    /** OS 展示串（未设置为 --） */
    osText: string;
    /** 版本串 */
    versionText: string;
  }

  interface Props {
    clusterType: ClusterTypes;
    /** 数据库类型（权限资源） */
    dbType: DBTypes;
    /** 各组件版本展示信息：存量模块未设置时为 {} 或部分缺失 */
    dbVersionInfo: Record<string, ComponentVersionInfo>;
    /** 模块 ID */
    moduleId: number;
  }

  const props = defineProps<Props>();

  const emit = defineEmits<(e: 'updated', dbVersionInfo: Record<string, ComponentVersionInfo>) => void>();

  const { t } = useI18n();

  /** 集群类型 → 组件展示配置（label + 协议组件名） */
  const layerConfigMap: Record<string, { componentName: string; label: string }[]> = {
    tendbcluster: [
      { componentName: 'remote', label: '存储层' },
      { componentName: 'spider', label: '接入层' },
    ],
    tendbha: [
      { componentName: 'backend', label: '存储层' },
      { componentName: 'proxy', label: '接入层' },
    ],
    tendbsingle: [{ componentName: 'single', label: '存储层' }],
  };

  /** 按层组装展示数据；存量模块 db_version_info 为 {} 时层仍展示但值为 --（首次编辑时选定模式） */
  const layerList = computed<LayerDisplay[]>(() => {
    const config = layerConfigMap[props.clusterType] || [];
    return config.map((item) => {
      const info = props.dbVersionInfo[item.componentName];
      // 协议 §5：版本记录被删时名称字段返回空串，需与 OS 列口径一致兜底为 --
      const versionText = info
        ? [info.distribution, info.version_series, info.version_name].filter(Boolean).join(' / ') || '--'
        : '--';
      const osText = info?.effective_permit_os?.length ? info.effective_permit_os.join('，') : '--';
      return {
        componentName: item.componentName,
        info,
        label: t(item.label),
        osText,
        versionText,
      };
    });
  });

  // ============ OS 编辑弹窗 ============
  const isShowOsDialog = ref(false);
  const isSubmitting = ref(false);
  const editingLayer = ref<LayerDisplay>();
  const specifyError = ref('');

  const dialogForm = reactive({
    osMode: 'follow' as 'follow' | 'specify',
    specifyOs: [] as string[],
  });

  /** 打开弹窗：回填当前模式与取值（-- 时默认跟随，首次编辑时选定模式） */
  const handleEditOs = (layer: LayerDisplay) => {
    editingLayer.value = layer;
    specifyError.value = '';
    dialogForm.osMode = layer.info && !layer.info.follow_package ? 'specify' : 'follow';
    dialogForm.specifyOs = [...(layer.info?.effective_permit_os ?? [])];
    isShowOsDialog.value = true;
  };

  const handleSpecifyChange = () => {
    specifyError.value = dialogForm.specifyOs.length === 0 ? t('请至少选择 1 个操作系统版本') : '';
  };

  /** 保存：update_module_version_os 只传要改的组件；跟随仅改模式即可；缩小指定范围可保存 */
  const { run: runUpdateOs } = useRequest(updateModuleVersionOs, {
    manual: true,
    onSuccess(res) {
      messageSuccess(t('操作成功'));
      isShowOsDialog.value = false;
      emit('updated', res.db_version_info);
    },
  });

  const handleSaveOs = () => {
    if (!editingLayer.value?.info) return;
    // 指定范围至少 1 项（§3.2）
    if (dialogForm.osMode === 'specify' && dialogForm.specifyOs.length === 0) {
      specifyError.value = t('请至少选择 1 个操作系统版本');
      return;
    }
    isSubmitting.value = true;
    runUpdateOs({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      db_module_id: props.moduleId,
      db_versions: {
        [editingLayer.value.componentName]: {
          permit_os: dialogForm.osMode === 'follow' ? [] : [...dialogForm.specifyOs],
          permit_os_type: 'Linux',
        },
      },
    });
    isSubmitting.value = false;
  };

  const handleDialogClosed = () => {
    isShowOsDialog.value = false;
    editingLayer.value = undefined;
  };
</script>

<style lang="less" scoped>
  .module-version-panel {
    position: relative;
    padding: 12px 0 16px;
    margin: 0 24px;

    &::before {
      position: absolute;
      top: -1px;
      right: 0;
      left: 0;
      height: 1px;
      background: #eaebf0;
      content: '';
    }

    /* 每层一个浅灰分组块：层名加粗，版本 / 操作系统版本同排，末尾编辑图标 */
    .version-layer-row {
      display: flex;
      min-height: 40px;
      padding: 0 16px;
      font-size: 12px;
      line-height: 20px;
      background: #f5f7fa;
      border-radius: 2px;
      box-sizing: border-box;
      gap: 32px;
      align-items: center;

      & + .version-layer-row {
        margin-top: 12px;
      }

      .layer-name {
        min-width: 48px;
        flex-shrink: 0;
        font-weight: 700;
        color: #313238;
      }

      .layer-version {
        color: #313238;
      }

      .layer-field-label {
        color: #63656e;
      }

      .layer-os-actions {
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }

      .layer-os {
        display: inline-flex;
        align-items: center;
        color: #313238;

        .os-empty {
          color: #c4c6cc;
        }
      }

      .layer-edit {
        width: 16px;
        height: 16px;
        min-width: 16px;
        padding: 0;
        font-size: 16px;
        line-height: 16px;
        color: #979ba5;
        flex-shrink: 0;

        &:hover {
          color: #3a84ff;
        }
      }
    }
  }

  .os-edit-body {
    padding: 8px 4px;

    .radio-desc {
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
    }

    .os-specify-select {
      width: 100%;
      margin-top: 8px;
    }

    .specify-error {
      margin-top: 4px;
      font-size: 12px;
      color: #ea3636;
    }
  }
</style>
