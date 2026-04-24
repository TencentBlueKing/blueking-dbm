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
        <template v-if="dbVersion?.full_version">
          <div class="split-line" />
          <div class="db-version-display">
            {{ dbVersion.full_version }}
          </div>
        </template>
        <BkTag
          class="ml-8"
          theme="info">
          {{ pkgLabel }}
        </BkTag>
        <BkTag theme="info">
          {{ releaseLabel }}
        </BkTag>
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
            v-model="formModel.version_series"
            :distribution-id="releaseVersion?.id"
            :version-series-id="versionSeriesId" />
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
              :placeholder="fullVersionPlaceholder" />
          </BkFormItem>
          <BkFormItem
            class="version-item"
            :label="t('版本名')"
            property="name"
            required>
            <BkInput v-model="formModel.name" />
          </BkFormItem>
          <BkFormItem
            class="version-item"
            :label="t('版本阶段')"
            property="phase"
            required>
            <VersionStage v-model="formModel.phase" />
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
            :title="t('请注意：不同文件间的操作系统版本不能重叠')" />
          <VersionFiles
            ref="versionFilesRef"
            :data="dbVersion?.packages"
            :db-type="dbType"
            :is-applied="isApplied"
            :pkg-type="pkgType"
            :version="formModel.full_version" />
        </BkFormItem>
        <BkFormItem
          :label="t('描述')"
          property="description">
          <BkInput
            v-model="formModel.description"
            :placeholder="t('请输入子版本描述，如：“修复 XX 漏洞”“优化性能”')"
            :resize="false"
            :rows="5"
            type="textarea" />
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
            theme="primary" />
        </BkFormItem>
      </BkForm>
      <div class="operate-main">
        <BkButton
          class="operate-button"
          :loading="
            createDbVersionLoading || batchCreatePackagesLoading || updateDbVersionLoading || batchDeletePackagesLoading
          "
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
  import { createDbVersion, updateDbVersion } from '@services/source/version';

  import { useBeforeClose } from '@hooks';

  import { messageSuccess } from '@utils';

  import VersionFiles from './components/version-files/Index.vue';
  import VersionSeries from './components/VersionSeries.vue';
  import VersionStage from './components/VersionStage.vue';

  interface Props {
    dbType: string;
    dbVersion?: DbVersionModel;
    isEdit?: boolean;
    pkgLabel?: string;
    pkgType: string;
    releaseLabel?: string;
    releaseVersion?: ReleaseVersionModel;
    versionSeriesId?: number;
  }

  type Emits = (e: 'success', versionSeriesId: number) => void;

  const props = withDefaults(defineProps<Props>(), {
    dbVersion: undefined,
    isEdit: false,
    pkgLabel: '',
    releaseLabel: '',
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

  const formRef = ref();
  const versionFilesRef = ref<InstanceType<typeof VersionFiles>>();
  const formModel = ref(initFormModel());

  const fullVersionPlaceholder = computed(() => props.dbType === 'mysql' ? t('请输入6位点分数字，如 1.2.1.0.0.1') : t('请输入3位点分数字，如 1.2.1'))
  const isApplied = computed(() => {
    const packages = props.dbVersion?.packages;
    return Array.isArray(packages) && packages.length > 0 && packages.some((item) => item.instances > 0);
  });

  const enableTip = `${t('启用：所有场景均可使用，如：部署、升级')}\n${t('停用：存量集群替换不受影响，其它场景不可使用。注意：停用将自动清除推荐')}`;

  const formRules = {
    version_series: [
      {
        message: t('请选择所属系列'),
        trigger: 'blur',
        validator: () => !!formModel.value.version_series,
      }
    ],
    files: [
      {
        message: t('请补全版本文件信息'),
        trigger: 'blur',
        validator: () => !!versionFilesRef.value!.getValue(),
      },
    ],
    full_version: [
      {
        message: () => props.dbType === 'mysql' ? t('请输入6位点分数字，如 1.2.1.0.0.1') : t('请输入3位点分数字，如 1.2.1'),
        trigger: 'blur',
        validator: (value: string) => props.dbType === 'mysql' ? /^(\d+\.){5}\d+$/.test(value) : /^(\d+\.){2}\d+$/.test(value),
      },
    ],
  };

  const handleBatchCreatePackages = (data: { id: number }) => {
    const versionFilesInfo = versionFilesRef.value!.getValue()!;
    const updateParams = versionFilesInfo.map((item) => ({
      ...item,
      db_type: props.dbType,
      db_version: data.id,
      enable: formModel.value.enable,
      permit_os: item.permit_os.length === 1 && item.permit_os[0] === 'all' ? [] : item.permit_os,
      permit_os_type: item.permit_os_type,
      pkg_type: props.pkgType,
      version: formModel.value.full_version,
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
      messageSuccess(props.isEdit ? t('更新成功') : t('新增成功'));
      formModel.value = initFormModel();
      isShow.value = false;
    },
  });

  const { loading: batchDeletePackagesLoading, run: runBatchDeletePackages } = useRequest(batchDeletePackages, {
    manual: true,
  });

  watch(
    () => props.dbVersion,
    () => {
      if (props.dbVersion) {
        formModel.value.version_series = props.dbVersion.version_series;
        formModel.value.full_version = props.dbVersion.full_version;
        formModel.value.name = props.dbVersion.name;
        formModel.value.phase = props.dbVersion.phase;
        formModel.value.description = props.dbVersion.description;
        formModel.value.enable = props.dbVersion.enable;
      } else {
        formModel.value = initFormModel();
      }
      setTimeout(() => {
        window.changeConfirm = false;
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    formModel,
    () => {
      window.changeConfirm = true;
    },
    {
      deep: true,
    },
  );

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
