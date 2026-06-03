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
        :rules="formRules">
        <BkFormItem
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
            @value-change="handleValueChange" />
        </BkFormItem>
        <div class="version-row">
          <BkFormItem
            class="version-item"
            :label="t('版本号')"
            property="full_version"
            required>
            <BkInput
              v-model="formModel.full_version"
              :disabled="!!dbVersion"
              :placeholder="fullVersionPlaceholder"
              @blur="handleResetDefaultVersionName"
              @input="handleValueChange" />
          </BkFormItem>
          <BkFormItem
            class="version-item"
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
              @input="handleValueChange" />
          </BkFormItem>
          <BkFormItem
            class="version-item"
            :label="t('版本阶段')"
            property="phase"
            required>
            <VersionStage
              v-model="formModel.phase"
              @value-change="handleValueChange" />
          </BkFormItem>
        </div>
        <BkFormItem
          :label="t('版本文件')"
          property="files"
          :required="!isEdit">
          <!-- <BkAlert
            v-if="isApplied"
            class="mb-8"
            closable
            theme="warning"
            :title="t('该版本已被应用，已上传的版本文件不可删除，仅支持追加')" /> -->
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
            :version="formModel.full_version"
            @value-change="handleValueChange" />
        </BkFormItem>
        <BkFormItem
          :label="t('描述')"
          property="description">
          <BkInput
            v-model="formModel.description"
            :placeholder="t('请输入子版本描述，如：“修复 XX 漏洞”“优化性能”')"
            :resize="false"
            :rows="5"
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

  const dbPkgSixMaxMap: Record<string, Record<string, boolean>> = {
    mysql: {
      mysql: true,
      spider: true,
    },
    redis: {
      twemproxy: true,
    },
  };

  const enableTip = `${t('启用：所有场景均可使用，如：部署、升级')}\n${t('停用：存量集群替换不受影响，其它场景不可使用。注意：停用将自动清除推荐')}`;

  const formRef = ref();
  const versionFilesRef = ref<InstanceType<typeof VersionFiles>>();
  const versionSeriesRef = ref<InstanceType<typeof VersionSeries>>();
  const formModel = ref(initFormModel());
  const confirmDisabled = ref(true);

  const isPureMysql = computed(() => props.dbType === 'mysql' && props.pkgType === 'mysql');

  const isFullVersionSixMax = computed(() => {
    return dbPkgSixMaxMap[props.dbType]?.[props.pkgType] ?? false;
  });

  const fullVersionPlaceholder = computed(() =>
    isFullVersionSixMax.value ? t('请输入6位点分数字，如 1.2.1.0.0.1') : t('请输入3位点分数字，如 1.2.1'),
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
        message: t('请补全版本文件信息'),
        trigger: 'blur',
        validator: () => !!versionFilesRef.value!.getValue(),
      },
    ],
    full_version: [
      {
        message: () =>
          isFullVersionSixMax.value ? t('请输入6位点分数字，如 1.2.1.0.0.1') : t('请输入3位点分数字，如 1.2.1'),
        trigger: 'blur',
        validator: (value: string) =>
          isFullVersionSixMax.value ? /^(\d+\.){5}\d+$/.test(value) : /^(\d+\.){2}\d+$/.test(value),
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
    const versionFilesInfo = versionFilesRef.value!.getValue()!;
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

  const { loading: batchDeletePackagesLoading, run: runBatchDeletePackages } = useRequest(batchDeletePackages, {
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
      window.changeConfirm = confirmDisabled.value;
    },
    {
      immediate: true,
    },
  );

  watch(isShow, () => {
    confirmDisabled.value = true;
  });

  const handleValueChange = () => {
    confirmDisabled.value = false;
  };

  const handleResetDefaultVersionName = () => {
    formModel.value.name = formModel.value.full_version ? defaultAutoVersionName.value : '';
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
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
      if (props.isEdit) {
        const versionFilesInfo = versionFilesRef.value!.getValue()!;
        const newPackageIds = versionFilesInfo.reduce<number[]>((results, item) => {
          if (item.id) {
            results.push(item.id);
          }
          return results;
        }, []);
        const oldPackageIds = props.dbVersion!.packages.map((item) => item.id);
        const packageIdsToDelete = _.difference(oldPackageIds, newPackageIds);
        if (packageIdsToDelete.length > 0) {
          runBatchDeletePackages({ package_ids: packageIdsToDelete });
        }
        runUpdateDbVersion({
          ...commonParams,
          id: props.dbVersion!.id,
          recommend: props.dbVersion!.recommend,
        });
      } else {
        runCreateDbVersion({
          ...commonParams,
          recommend: false,
        });
      }
    });
  };

  const handleCancel = () => {
    isShow.value = false;
    if (props.isEdit) {
      formModel.value = initFormModelFromProps();
      return;
    }
    formModel.value = initFormModel();
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

        .enable-tip-icon {
          margin-left: 4px;
          font-size: 14px;
          color: #979ba5;
          cursor: pointer;
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
