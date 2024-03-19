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
  <ApplyPermissionCatch>
    <div class="version-files">
      <BkTab
        v-model:active="state.active"
        type="card">
        <BkTabPanel
          v-for="tab of tabs"
          :key="tab.name"
          :label="tab.label"
          :name="tab.name" />
      </BkTab>
      <div class="version-files-content">
        <div class="version-files-operations">
          <AuthButton
            action-id="package_manage"
            :resource="props.info.name"
            theme="primary"
            @click="handleCreate">
            {{ t('新增') }}
          </AuthButton>
          <BkInput
            v-model="state.search"
            clearable
            :placeholder="t('请输入名称关键字')"
            style="width: 500px"
            type="search"
            @clear="handleChangePage(1)"
            @enter="handleChangePage(1)" />
        </div>
        <BkLoading :loading="state.isLoading">
          <DbOriginalTable
            class="version-files-table"
            :columns="columns"
            :data="state.data"
            :is-anomalies="state.isAnomalies"
            :is-searching="!!state.search"
            :max-height="tableMaxHeight"
            :pagination="state.pagination"
            remote-pagination
            @clear-search="handleClearSearch"
            @page-limit-change="handeChangeLimit"
            @page-value-change="handleChangePage"
            @refresh="fetchPackages" />
        </BkLoading>
      </div>
    </div>
    <!-- 新增版本 -->
    <BkDialog
      v-model:is-show="createFileState.isShow"
      height="auto"
      :mask-close="false"
      theme="primary"
      :title="t('新增版本')"
      :width="480">
      <BkForm
        ref="versionFormRef"
        class="create-dialog-operations"
        form-type="vertical"
        :model="createFileState.formdata"
        :rules="rules">
        <BkFormItem
          :label="t('版本名称')"
          property="version"
          required>
          <template v-if="isInputType">
            <BkInput
              v-model="createFileState.formdata.version"
              :placeholder="t('请输入')" />
          </template>
          <template v-else>
            <BkSelect
              v-model="createFileState.formdata.version"
              :clearable="false"
              filterable
              :input-search="false"
              :loading="createFileState.isLoadVersions">
              <BkOption
                v-for="version of createFileState.versions"
                :key="version"
                :label="version"
                :value="version" />
            </BkSelect>
          </template>
        </BkFormItem>
        <BkFormItem
          class="pb-16"
          :label="t('文件')"
          property="name"
          required>
          <BkUpload
            ref="uplodRef"
            v-bk-tooltips="fileTips"
            :accept="acceptInfo.accept"
            :disabled="!createFileState.formdata.version"
            :form-data-attributes="uploadAttributes"
            :header="{ name: 'X-CSRFToken', value: Cookies.get('dbm_csrftoken') }"
            :multiple="false"
            name="file"
            :size="1024"
            :tip="acceptInfo.tips"
            :url="createFileState.uploadUrl"
            with-credentials
            @delete="handleDeleteFile"
            @success="handleUpdateSuccess" />
        </BkFormItem>
      </BkForm>
      <template #footer>
        <BkButton
          class="mr-8"
          :loading="createFileState.isLoading"
          theme="primary"
          @click="handleConfirmCreate">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          :disabled="createFileState.isLoading"
          @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkDialog>
  </ApplyPermissionCatch>
</template>
<script setup lang="tsx">
  import { Form, Message } from 'bkui-vue';
  import Cookies from 'js-cookie';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import VersionFileModel from '@services/model/version-file/version-file';
  import {
    createPackage,
    updatePackage,
  } from '@services/source/package';
  import { getVersions } from '@services/source/version';

  import {
    useCopy,
    useDefaultPagination,
    useTableMaxHeight,
  } from '@hooks';

  import { DBTypes } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/catch.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    messageSuccess,
  } from '@utils';

  import { useVersionFiles } from '../hooks/useVersionFiles';

  import type { IState, VersionFileType } from './types';


  interface Props {
    info: VersionFileType,
    pkgTypeList: string[],
  }

  const props = defineProps<Props>();

  const initCreateFormdata = () => ({
    version: '',
    name: '',
    path: '',
    size: 0,
    md5: '',
  });

  const { t } = useI18n();
  const copy = useCopy();
  const tableMaxHeight = useTableMaxHeight(340);

  const state = reactive<IState>({
    active: '',
    isLoading: false,
    isAnomalies: false,
    pagination: useDefaultPagination(),
    data: [] as VersionFileModel[],
    search: '',
  });
  // 类型参数
  const typeParams = computed(() => ({
    db_type: props.info.name,
    pkg_type: state.active,
  }));
  const tabs = computed(() => props.info.children || []);
  // 版本是否为输入框
  const isInputType = computed(() => {
    const bigData: string[] = [DBTypes.KAFKA, DBTypes.ES, DBTypes.HDFS, DBTypes.PULSAR, DBTypes.INFLUXDB];
    return (bigData.includes(props.info.name) && state.active !== 'actuator' || props.info.name === DBTypes.MONGODB);
  });
  const fileTips = computed(() => ({
    content: isInputType.value ? t('请输入版本名称') : t('请选择版本名称'),
    disabled: !!createFileState.formdata.version,
  }));

  /** 操作列表基础方法 */
  const {
    fetchPackages,
    handleChangePage,
    handeChangeLimit,
    handleConfirmDelete,
  } = useVersionFiles(state, typeParams);

  /** 新增文件功能 */
  const createFileState = reactive({
    isShow: false,
    isLoading: false,
    isLoadVersions: false,
    uploadUrl: `${window.location.origin}/apis/packages/upload/`,
    versions: [] as string[],
    formdata: initCreateFormdata(),
  });

  const versionFormRef = ref<InstanceType<typeof Form>>();
  // 上传文件附带参数
  const uploadAttributes = computed(() => ([
    { name: 'version', value: createFileState.formdata.version },
    { name: 'pkg_type', value: state.active },
    { name: 'db_type', value: props.info.name },
  ]));

  const acceptInfo = computed(() => {
    const limitTypes = ['mysql', 'mysql-proxy'];
    if (limitTypes.includes(state.active)) {
      return {
        accept: 'tar.gz',
        tips: t('支持上传tar_gz压缩格式文件_文件大小不超过1GB'),
      };
    }
    return {
      accept: '',
      tips: t('文件大小不超过1GB'),
    };
  });

  const isShowSwitch = computed(() => props.pkgTypeList.length > 0 && props.pkgTypeList.includes(state.active));

  const columns = computed(() => {
    const basicColumns = [
      {
        label: t('版本名称'),
        field: 'version',
        render: ({ data }: { data: VersionFileModel }) => (
          <div class="version-name text-overflow" v-overflow-tips>
            {data.version}
            {data.priority > 0 && <bk-tag theme="info" class="ml-5">{t('默认')}</bk-tag>}
            {data.priority === 0 && (
              <bk-button
                v-bk-tooltips={{
                  disabled: data.enable,
                  content: t('未启用的版本不能设为默认'),
                }}
                class={{ 'set-btn': true, 'set-btn-disable': !data.enable }}
                size="small"
                onClick={() => handleSetDefaultVersion(data)}
              >
              {t('设为默认版本')}
              </bk-button>
            )}
          </div>
        ),
      },
      {
        label: t('文件名称'),
        field: 'name',
        render: ({ data }: { data: VersionFileModel }) => data.name || '--',
      },
      {
        label: 'MD5',
        field: 'md5',
        render: ({ data }: { data: VersionFileModel }) => (
          <TextOverflowLayout>
            {{
              default: () => data.md5,
              append: () => (
                <db-icon
                  type="copy"
                  onClick={() => copy(data.md5)} />
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('更新人'),
        field: 'updater',
        render: ({ data }: { data: VersionFileModel }) => data.updater || '--',
      },
      {
        label: t('更新时间'),
        field: 'update_at',
        render: ({ data }: { data: VersionFileModel }) => data.updateAtDisplay || '--',
      },
      {
        label: t('操作'),
        field: 'id',
        width: 100,
        render: ({ data }: { data: VersionFileModel }) => (
          <auth-button
            action-id="package_manage"
            resource={props.info.name}
            permission={data.permission.package_manage}
            text
            theme="primary"
            onClick={() => handleConfirmDelete(data)}>
            { t('删除') }
          </auth-button>
        ),
      },
    ];
    if (isShowSwitch.value) {
      const switchColumn = {
        label: t('是否启用'),
        field: 'enable',
        render: ({ data }: { data: VersionFileModel }) => (
          <bk-pop-confirm
            title={data.enable ? t('确认停用该版本？') : t('确认启用该版本？')}
            content={data.enable ? t('停用后，在选择版本时，将不可见，且不可使用') : t('启用后，在选择版本时，将开放选择')}
            width="308"
            placement="bottom"
            trigger="click"
            confirm-text={data.enable ? t('停用') : t('启用')}
            onConfirm={() => handleConfirmSwitch(data)}
          >
            <auth-switcher
              action-id="package_manage"
              resource={props.info.name}
              permission={data.permission.package_manage}
              size="small"
              model-value={data.enable}
              theme="primary"
            />
          </bk-pop-confirm>
        ),
      };
      basicColumns.splice(2, 1, switchColumn);
    }
    return basicColumns;
  });

  const rules = {
    version: [{
      required: true,
      message: t('必填'),
      trigger: 'blur',
    }],
    name: [{
      required: true,
      message: t('文件不能为空'),
      trigger: 'change',
      validator: (val: string[]) => val.length > 0,
    }],
  };

  const { run: runUpdatePackage } = useRequest(updatePackage, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchPackages();
    },
  });

  const handleSetDefaultVersion = (row: VersionFileModel) => {
    if (!row.enable) {
      return;
    }
    runUpdatePackage({
      id: row.id,
      priority: 1,
    });
  };

  const handleConfirmSwitch = async (row: VersionFileModel) => {
    runUpdatePackage({
      id: row.id,
      enable: !row.enable,
    });
  };

  function handleClearSearch() {
    state.search = '';
    handleChangePage(1);
  }


  /**
   * 获取版本号列表
   */
  const fetchVersions = () => {
    createFileState.isLoadVersions = true;
    getVersions({
      query_key: state.active,
      db_type: props.info.name,
    }, {
      permission: 'catch',
    })
      .then((res) => {
        createFileState.versions = res;
      })
      .finally(() => {
        createFileState.isLoadVersions = false;
      });
  };

  watch(() => state.active, (value, old) => {
    if (value && value !== old) {
      state.search = '';
      handleChangePage(1);
      // 大数据类型和 Mongodb 不需要拉取版本
      if (!isInputType.value) {
        fetchVersions();
      }
    }
  }, { immediate: true });

  /**
   * 新增版本
   */
  const handleCreate = () => {
    createFileState.isShow = true;
  };

  /**
   * 取消新增
   */
  const handleClose = () => {
    createFileState.isShow = false;
    Object.assign(createFileState.formdata, initCreateFormdata());
  };

  /**
   * 提交新增版本
   */
  const handleConfirmCreate = async () => {
    await versionFormRef.value?.validate();

    createFileState.isLoading = true;
    createPackage({
      ...createFileState.formdata,
      ...typeParams.value,
    })
      .then(() => {
        Message({
          message: t('新增成功'),
          theme: 'success',
        });
        handleClose();
        handleChangePage(1);
      })
      .finally(() => {
        createFileState.isLoading = false;
      });
  };

  /**
   * 文件上传成功
   */
  const handleUpdateSuccess = (file: any) => {
    Object.assign(createFileState.formdata, file?.data || {});
    versionFormRef.value?.clearValidate();
  };

  /**
   * 文件删除
   */
  const handleDeleteFile = () => {
    Object.assign(createFileState.formdata, initCreateFormdata());
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .version-files {
    padding: 24px;

    .version-files-content {
      padding: 16px;
      background: #fff;
    }

    .version-files-operations {
      margin-bottom: 16px;
      justify-content: space-between;
      .flex-center();

      .bk-button {
        width: 88px;
      }
    }

    .bk-tab {
      background-color: #fafbfd;
    }

    :deep(.bk-tab-content) {
      padding: 0;
    }

    :deep(.bk-tab-header--active) {
      background-color: @bg-white;
    }
  }

  .version-files-table {
    :deep(.bk-table-body) {
      .md-five {
        display: flex;

        .md-five-value {
          display: inline-block;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .db-icon-copy {
          display: none;
          margin-left: 12px;
          line-height: 40px;
          color: @primary-color;
          cursor: pointer;
        }
      }

      .version-name {
        .set-btn {
          display: none;
          height: 22px;
          padding: 3px 8px;
          margin-left: 5px;
          cursor: pointer;
          background: #fafbfd;
          border: 1px solid #dcdee5;
        }

        .set-btn-disable {
          color: #c4c6cc;
        }
      }

      tr:hover .db-icon-copy {
        display: inline-block;
      }

      tr:hover {
        .set-btn {
          display: inline-flex;
        }
      }
    }
  }

  .create-dialog-operations {
    margin-bottom: 16px;

    .bk-button {
      min-width: 64px;
    }
  }

  :deep(.bk-upload__tip) {
    line-height: normal;
  }
</style>
