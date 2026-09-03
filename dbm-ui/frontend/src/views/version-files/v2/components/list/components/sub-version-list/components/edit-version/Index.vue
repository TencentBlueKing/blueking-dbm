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
  <BkSideslider
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    class="edit-version-slider-main"
    render-directive="if"
    :width="960"
    @closed="handleCancel">
    <template #header>
      <div class="header-main">
        <span>{{ props.isEdit ? t('编辑版本') : t('添加版本') }}</span>
        <div class="split-line" />
        <div class="db-version-display">
          {{ formModel.name ? formModel.name : t('未命名') }}
        </div>
      </div>
    </template>
    <div class="content-main">
      <BkForm
        ref="formRef"
        class="form-main"
        form-type="vertical"
        :model="formModel"
        :rules="formRules"
        @validate="handleFormValidate">
        <BkFormItem
          :class="{ 'is-hide-tip': !formModel.version_series }"
          property="version_series"
          required>
          <template #label>
            <span>{{ t('所属系列') }}</span>
            <span class="series-tip">({{ t('同一版本系列代表核心功能兼容，支持原地升级') }})</span>
          </template>
          <VersionSeries
            ref="versionSeriesRef"
            v-model="formModel.version_series"
            :distribution-id="releaseVersion?.id"
            :version-series-id="versionSeriesId"
            @add-version="() => emits('addVersion')"
            @label-change="handleLabelChange"
            @value-change="handleValueChange" />
        </BkFormItem>
        <div class="version-row">
          <BkFormItem
            class="version-item"
            :class="{ 'is-hide-tip': !formModel.full_version }"
            :label="t('版本号')"
            property="full_version"
            required>
            <BkInput
              v-model="formModel.full_version"
              :disabled="!!dbVersion"
              :maxlength="50"
              :placeholder="t('请输入xx', [t('版本号')])"
              show-word-limit
              @blur="handleResetDefaultVersionName"
              @input="handleValueChange" />
            <div
              v-if="!hideTipMap.full_version && !isEdit"
              class="item-tip">
              {{ fullVersionPlaceholder }}
            </div>
          </BkFormItem>
          <BkFormItem
            class="version-item version-name-item"
            :class="{ 'is-hide-tip': !formModel.name }"
            :label="t('版本名')"
            property="name"
            required>
            <BkButton
              v-if="formModel.name && formModel.name !== defaultAutoVersionName"
              class="reset-default-btn"
              size="small"
              text
              theme="primary"
              @click="handleResetDefaultVersionName">
              {{ t('重置为默认') }}
            </BkButton>
            <BkInput
              v-model="formModel.name"
              :maxlength="50"
              :placeholder="t('请输入xx', [t('版本名')])"
              show-word-limit
              @input="handleValueChange" />
            <div
              v-if="!hideTipMap.name"
              class="item-tip">
              {{ t('仅支持字母、数字、连字符、下划线、点号，可随时修改') }}
            </div>
          </BkFormItem>
          <BkFormItem
            class="version-item"
            :class="{ 'is-hide-tip': !formModel.phase }"
            :label="t('版本阶段')"
            property="phase"
            required>
            <VersionStage
              v-model="formModel.phase"
              @value-change="handleValueChange" />
          </BkFormItem>
        </div>
        <BkFormItem
          class="mt-16"
          :label="t('版本文件')"
          property="files"
          :required="!isEdit">
          <BkAlert
            class="mb-8"
            closable
            theme="warning"
            :title="t('任意两个文件不能覆盖同一个 OS 版本，否则部署版本时系统无法判定使用哪一份。')" />
          <VersionFiles
            ref="versionFilesRef"
            :data="dbVersion?.packages"
            :db-type="dbType"
            :is-applied="isApplied"
            :pkg-type="pkgType"
            :version="versionSeriesLabel"
            @value-change="handleValueChange" />
        </BkFormItem>
        <BkFormItem
          :label="t('描述')"
          property="description">
          <BkInput
            v-model="formModel.description"
            :maxlength="500"
            :placeholder="t('请输入子版本描述，如：“修复 XX 漏洞”“优化性能”')"
            :resize="false"
            :rows="5"
            show-word-limit
            type="textarea"
            @input="handleValueChange" />
        </BkFormItem>
        <BkFormItem
          property="enable"
          required>
          <template #label>
            <span>{{ t('是否启用') }}</span>
            <DbIcon
              v-bk-tooltips="enableTip"
              class="enable-tip-icon"
              type="help" />
          </template>
          <BkSwitcher
            v-model="formModel.enable"
            theme="primary"
            @change="handleValueChange" />
        </BkFormItem>
      </BkForm>
      <div class="operate-main">
        <BkButton
          v-bk-tooltips="{
            disabled: !confirmDisabled,
            content: t('当前无变更，请先修改内容'),
          }"
          class="operate-button"
          :disabled="confirmDisabled || confirmLoading"
          :loading="confirmLoading"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="operate-button"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { batchCreatePackages, batchDeletePackages } from '@services/source/package';
  import { checkDbversionNameConflict, createDbVersion, updateDbVersion } from '@services/source/version';

  import { useBeforeClose } from '@hooks';

  import { CHINESE_CHAR_REG, IDENTIFIER_NAME_REG, isPureMysqlPkgType } from '@views/version-files/v2/common';

  import { messageSuccess } from '@utils';

  import VersionFiles from './components/version-files/Index.vue';
  import VersionSeries from './components/VersionSeries.vue';
  import VersionStage from './components/VersionStage.vue';

  interface Props {
    dbType: string;
    dbVersion?: DbVersionModel;
    isEdit?: boolean;
    pkgType: string;
    releaseVersion?: ReleaseVersionModel;
    versionNum: number;
    versionSeriesId?: number;
  }

  interface Emits {
    (e: 'success', versionSeriesId: number): void;
    (e: 'addVersion'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbVersion: undefined,
    isEdit: false,
    releaseVersion: undefined,
    versionSeriesId: undefined,
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const initFormModel = () => ({
    description: '',
    enable: true,
    files: ['default'],
    full_version: '',
    name: '',
    phase: '',
    version_series: 0,
  });

  const initFormModelFromProps = () => ({
    description: props.dbVersion!.description,
    enable: props.dbVersion!.enable,
    files: ['default'],
    full_version: props.dbVersion!.full_version,
    name: props.dbVersion!.name,
    phase: props.dbVersion!.phase,
    version_series: props.dbVersion!.version_series,
  });

  const enableTip = `${t('启用：所有场景均可使用，如：部署、升级')}\n${t('停用：存量集群替换不受影响，其它场景不可使用。注意：停用将自动清除推荐')}`;
  let fileErrorMessage = '';

  const formRef = ref();
  const versionFilesRef = ref<InstanceType<typeof VersionFiles>>();
  const versionSeriesRef = ref<InstanceType<typeof VersionSeries>>();
  const formModel = ref(initFormModel());
  const confirmDisabled = ref(true);
  const versionSeriesLabel = ref('');
  const hideTipMap = ref({
    full_version: false,
    name: false,
  });

  const isPureMysql = computed(() => isPureMysqlPkgType(props.dbType, props.pkgType));

  const fullVersionPlaceholder = computed(() =>
    props.versionNum === 6 ? t('6 段点分数字，如 8.0.3.1.0.0') : t('3 段点分数字，如 5.0.14'),
  );
  const isApplied = computed(() => {
    const packages = props.dbVersion?.packages;
    return Array.isArray(packages) && packages.length > 0 && packages.some((item) => item.instances > 0);
  });

  const defaultAutoVersionName = computed(() =>
    isPureMysql.value
      ? `${props.pkgType.toLocaleLowerCase()}_${props.releaseVersion?.name.toLocaleLowerCase()}_${formModel.value.full_version}`
      : `${props.pkgType}_${formModel.value.full_version}`,
  );

  const confirmLoading = computed(() => {
    return (
      createDbVersionLoading.value ||
      batchCreatePackagesLoading.value ||
      updateDbVersionLoading.value ||
      batchDeletePackagesLoading.value
    );
  });

  const formRules = computed(() => ({
    files: [
      {
        message: () => fileErrorMessage,
        trigger: 'blur',
        validator: () => {
          const value = versionFilesRef.value!.getValue();
          if (typeof value === 'string') {
            fileErrorMessage = value;
            return false;
          }
          fileErrorMessage = '';
          return true;
        },
      },
    ],
    full_version: [
      {
        message: t('格式不正确，须为 {n} 段点分数字', { n: props.versionNum }),
        trigger: 'blur',
        validator: (value: string) =>
          props.versionNum === 6 ? /^(\d+\.){5}\d+$/.test(value) : /^(\d+\.){2}\d+$/.test(value),
      },
      {
        message: t('该版本号已存在'),
        validator: async (value: string) => {
          if (props.isEdit || !formModel.value.version_series) {
            return true;
          }

          const result = await checkDbversionNameConflict({
            full_version: value,
            version_series: formModel.value.version_series,
          });
          return !result.version_conflict;
        },
      },
    ],
    name: [
      {
        message: t('请勿使用中文'),
        trigger: 'blur',
        validator: (value: string) => !CHINESE_CHAR_REG.test(value),
      },
      {
        message: t('格式不正确，请勿使用空格或特殊符号'),
        trigger: 'blur',
        validator: (value: string) => IDENTIFIER_NAME_REG.test(value),
      },
      {
        message: t('该版本名已存在'),
        validator: async (value: string) => {
          if (props.dbVersion?.name === value || !formModel.value.version_series) {
            return true;
          }

          const result = await checkDbversionNameConflict({
            name: value,
            version_series: formModel.value.version_series,
          });
          return !result.name_conflict;
        },
      },
    ],
    version_series: [
      {
        message: t('请选择所属系列'),
        trigger: 'blur',
        validator: () => !!formModel.value.version_series,
      },
    ],
  }));

  const handleBatchCreatePackages = (data: { id: number }) => {
    const value = versionFilesRef.value!.getValue()!;
    const versionFilesInfo = typeof value === 'string' ? [] : value;
    const seriesLabel = versionSeriesRef.value!.getCurrentLabel();
    const updateParams = versionFilesInfo.map((item) => ({
      ...item,
      db_type: props.dbType,
      db_version: data.id,
      enable: formModel.value.enable,
      permit_os: item.permit_os.length === 1 && item.permit_os[0] === 'all' ? [] : item.permit_os,
      permit_os_type: item.permit_os_type,
      pkg_type: props.pkgType,
      version: seriesLabel,
    }));
    runBatchCreatePackages({ packages: updateParams });
  };

  const { loading: createDbVersionLoading, run: runCreateDbVersion } = useRequest(createDbVersion, {
    manual: true,
    onSuccess: handleBatchCreatePackages,
  });

  const { loading: updateDbVersionLoading, run: runUpdateDbVersion } = useRequest(updateDbVersion, {
    manual: true,
    onSuccess: handleBatchCreatePackages,
  });

  const { loading: batchCreatePackagesLoading, run: runBatchCreatePackages } = useRequest(batchCreatePackages, {
    manual: true,
    onSuccess: () => {
      emits('success', formModel.value.version_series);
      messageSuccess(t('操作成功'));
      formModel.value = initFormModel();
      isShow.value = false;
    },
  });

  const { loading: batchDeletePackagesLoading, runAsync: runBatchDeletePackages } = useRequest(batchDeletePackages, {
    manual: true,
  });

  watch(
    () => [props.isEdit, props.dbVersion],
    () => {
      if (props.isEdit) {
        formModel.value = initFormModelFromProps();
      } else {
        formModel.value = initFormModel();
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    confirmDisabled,
    () => {
      window.changeConfirm = !confirmDisabled.value;
    },
    {
      immediate: true,
    },
  );

  watch(isShow, () => {
    confirmDisabled.value = true;
  });

  const handleLabelChange = (label: string) => {
    versionSeriesLabel.value = label;
  };

  const handleValueChange = () => {
    confirmDisabled.value = false;
  };

  const handleResetDefaultVersionName = () => {
    formModel.value.name = formModel.value.full_version ? defaultAutoVersionName.value : '';
  };

  const handleFormValidate = (property: string, result: boolean) => {
    hideTipMap.value[property as keyof typeof hideTipMap.value] =
      !result && !!formModel.value[property as keyof typeof formModel.value];
  };

  const handleSubmit = async () => {
    await formRef.value.validate();
    const commonParams = {
      description: formModel.value.description,
      distribution_snapshot: {
        db_type: props.dbType,
        engine: props.releaseVersion!.engine,
        id: props.releaseVersion!.id,
        name: props.releaseVersion!.name,
        pkg_type: props.pkgType,
      },
      enable: formModel.value.enable,
      full_version: formModel.value.full_version,
      name: formModel.value.name,
      phase: formModel.value.phase,
      version_series: formModel.value.version_series,
    };
    if (!props.isEdit) {
      runCreateDbVersion({
        ...commonParams,
        recommend: false,
      });
      return;
    }

    const value = versionFilesRef.value!.getValue()!;
    const versionFilesInfo = typeof value === 'string' ? [] : value;
    const newPackageIds = versionFilesInfo.reduce<number[]>((results, item) => {
      if (item.id) {
        results.push(item.id);
      }
      return results;
    }, []);
    const oldPackageIds = props.dbVersion!.packages.map((item) => item.id);
    const packageIdsToDelete = _.difference(oldPackageIds, newPackageIds);
    // 先等文件删除完成再更新版本，避免删除失败时版本已经改掉、文件却还挂在上面
    if (packageIdsToDelete.length > 0) {
      await runBatchDeletePackages({ package_ids: packageIdsToDelete });
    }
    runUpdateDbVersion({
      ...commonParams,
      id: props.dbVersion!.id,
      recommend: props.dbVersion!.recommend,
    });
  };

  const handleCancel = () => {
    isShow.value = false;
    if (props.isEdit) {
      formModel.value = initFormModelFromProps();
      return;
    }
    formModel.value = initFormModel();
    hideTipMap.value = {
      full_version: false,
      name: false,
    };
  };
</script>
<style lang="less">
  .edit-version-slider-main {
    .header-main {
      display: flex;
      align-items: center;

      .split-line {
        width: 1px;
        height: 14px;
        margin: 0 8px;
        background-color: #dcdee5;
      }

      .db-version-display {
        font-size: 14px;
        color: #979ba5;
      }

      .bk-tag {
        background-color: #e1ecff;

        .bk-tag-text {
          color: #1768ef;
        }
      }
    }

    .content-main {
      padding: 0 24px;

      .form-main {
        margin-top: 16px;

        .version-row {
          display: flex;
          gap: 52px;

          .version-item {
            flex: 1;
            position: relative;

            &.version-name-item {
              min-width: 300px;
            }

            .reset-default-btn {
              position: absolute;
              top: -22px;
              right: 0;
              font-size: 12px;
            }
          }
        }

        .series-tip {
          position: absolute;
          left: 66px;
          font-size: 12px;
          color: #979ba5;
        }

        .item-tip {
          position: absolute;
          top: 28px;
          font-size: 12px;
          color: #979ba5;
        }

        .enable-tip-icon {
          margin-left: 4px;
          font-size: 14px;
          color: #979ba5;
          cursor: pointer;
        }

        .is-hide-tip {
          .bk-form-error {
            display: none;
          }
        }
      }

      .operate-main {
        display: flex;
        gap: 8px;
        margin-top: 32px;

        .operate-button {
          width: 88px;
        }
      }
    }
  }
</style>
