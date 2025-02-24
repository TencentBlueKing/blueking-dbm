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
    <div class="version-files-file-content">
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
            :data="state.data"
            :is-anomalies="state.isAnomalies"
            :is-searching="!!state.search"
            :max-height="tableMaxHeight"
            :pagination="state.pagination"
            remote-pagination
            @clear-search="handleClearSearch"
            @page-limit-change="handeChangeLimit"
            @page-value-change="handleChangePage"
            @refresh="fetchPackages">
            <BkTableColumn
              field="version"
              :label="t('版本名称')"
              :min-width="300">
              <template #default="{ data }: { data: VersionFileModel }">
                <TextOverflowLayout>
                  {{ data.version }}
                  <template #append>
                    <BkButton
                      v-if="data.priority === 0"
                      v-bk-tooltips="{
                        disabled: data.enable,
                        content: t('未启用的版本不能设为默认'),
                      }"
                      class="set-btn"
                      :class="{
                        'set-btn-disable': !data.enable,
                      }"
                      size="small"
                      @click="() => handleSetDefaultVersion(data)">
                      {{ t('设为默认版本') }}
                    </BkButton>
                    <BkTag
                      v-else
                      class="ml-5"
                      size="small"
                      theme="info">
                      {{ t('默认') }}
                    </BkTag>
                  </template>
                </TextOverflowLayout>
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="name"
              :label="t('文件名称')"
              :min-width="350">
              <template #default="{ data }: { data: VersionFileModel }">
                {{ data.name || '--' }}
              </template>
            </BkTableColumn>
            <BkTableColumn
              v-if="isShowSwitch"
              :field="t('是否启用')"
              label="enable"
              :width="120">
              <template #default="{ data }: { data: VersionFileModel }">
                <BkPopConfirm
                  :confirm-text="data.enable ? t('停用') : t('启用')"
                  :content="
                    data.enable
                      ? t('停用后，在选择版本时，将不可见，且不可使用')
                      : t('启用后，在选择版本时，将开放选择')
                  "
                  placement="bottom"
                  :title="data.enable ? t('确认停用该版本？') : t('确认启用该版本？')"
                  trigger="click"
                  width="308"
                  @confirm="() => handleConfirmSwitch(data)">
                  <AuthSwitcher
                    action-id="package_manage"
                    :model-value="data.enable"
                    :permission="data.permission.package_manage"
                    :resource="info.name"
                    size="small"
                    theme="primary" />
                </BkPopConfirm>
              </template>
            </BkTableColumn>
            <BkTableColumn
              v-else
              field="md5"
              label="MD5"
              :width="350">
              <template #default="{ data }: { data: VersionFileModel }">
                <TextOverflowLayout>
                  {{ data.md5 }}
                  <template #append>
                    <DbIcon
                      type="copy"
                      @click="() => execCopy(data.md5, t('复制成功，共n条', { n: 1 }))" />
                  </template>
                </TextOverflowLayout>
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="updater"
              :label="t('更新人')"
              :width="120">
              <template #default="{ data }: { data: VersionFileModel }">
                {{ data.updater || '--' }}
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="updateAtDisplay"
              :label="t('更新时间')"
              :width="250">
              <template #default="{ data }: { data: VersionFileModel }">
                {{ data.updateAtDisplay || '--' }}
              </template>
            </BkTableColumn>
            <BkTableColumn
              :label="t('操作')"
              :width="120">
              <template #default="{ data }: { data: VersionFileModel }">
                <AuthButton
                  action-id="package_manage"
                  :permission="data.permission.package_manage"
                  :resource="info.name"
                  text
                  theme="primary"
                  @click="() => handleConfirmDelete(data)">
                  {{ t('删除') }}
                </AuthButton>
              </template>
            </BkTableColumn>
          </DbOriginalTable>
        </BkLoading>
      </div>
    </div>
  </ApplyPermissionCatch>
  <!-- 新增版本 -->
  <BkDialog
    v-model:is-show="createFileState.isShow"
    :mask-close="false"
    render-directive="if"
    theme="primary"
    :title="t('新增版本')"
    :width="480">
    <BkForm
      ref="versionFormRef"
      class="create-new-version-dialog"
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
          :before-upload="handleBeforeUpload"
          :custom-request="handleCustomRequest"
          :disabled="!createFileState.formdata.version"
          :header="[
            {
              name: 'Content-Type',
              value: 'application/octet-stream',
            },
            {
              name: 'X-CSRFToken',
              value: Cookies.get('dbm_csrftoken'),
            },
            {
              name: 'X-BKREPO-OVERWRITE',
              value: true,
            },
          ]"
          method="put"
          :multiple="false"
          name=""
          :size="10240"
          :tip="acceptInfo.tips"
          :url="createFileState.uploadUrl"
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
</template>
<script setup lang="ts">
  import { Form, Message } from 'bkui-vue';
  import type { UploadProgressEvent, UploadRequestOptions } from 'bkui-vue/lib/upload/upload.type';
  import Cookies from 'js-cookie';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import VersionFileModel from '@services/model/version-file/version-file';
  import { createPackage, updatePackage } from '@services/source/package';
  import { createBkrepoAccessToken } from '@services/source/storage';
  import { getVersions } from '@services/source/version';

  import { useDefaultPagination, useTableMaxHeight } from '@hooks';

  import { DBTypes } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, messageSuccess } from '@utils';

  import { useVersionFiles } from '../hooks/useVersionFiles';

  import type { IState, VersionFileType } from './types';

  interface Props {
    info: VersionFileType;
    pkgTypeList: string[];
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
  const tableMaxHeight = useTableMaxHeight(340);

  const uplodRef = ref();
  const versionFormRef = ref<InstanceType<typeof Form>>();

  const state = reactive<IState>({
    active: '',
    isLoading: false,
    isAnomalies: false,
    pagination: useDefaultPagination(),
    data: [] as VersionFileModel[],
    search: '',
  });

  /** 新增文件功能 */
  const createFileState = reactive({
    isShow: false,
    isLoading: false,
    isLoadVersions: false,
    uploadUrl: '',
    versions: [] as string[],
    formdata: initCreateFormdata(),
  });

  // 类型参数
  const typeParams = computed(() => ({
    db_type: props.info.name,
    pkg_type: state.active,
  }));
  const tabs = computed(() => props.info.children || []);
  // 版本是否为输入框
  const isInputType = computed(() => {
    const bigData: string[] = [
      DBTypes.KAFKA,
      DBTypes.ES,
      DBTypes.HDFS,
      DBTypes.PULSAR,
      DBTypes.INFLUXDB,
      DBTypes.DORIS,
    ];
    return (bigData.includes(props.info.name) && state.active !== 'actuator') || props.info.name === DBTypes.MONGODB;
  });
  const fileTips = computed(() => ({
    content: isInputType.value ? t('请输入版本名称') : t('请选择版本名称'),
    disabled: !!createFileState.formdata.version,
  }));

  const acceptInfo = computed(() => {
    const limitTypes = ['mysql', 'mysql-proxy'];
    if (limitTypes.includes(state.active)) {
      return {
        accept: '.tar.gz,.tar.xz',
        tips: t('支持上传tar_gz压缩格式文件_文件大小不超过1GB'),
      };
    }
    return {
      accept: '',
      tips: t('文件大小不超过1GB'),
    };
  });

  const isShowSwitch = computed(() => props.pkgTypeList.length > 0 && props.pkgTypeList.includes(state.active));

  const rules = {
    version: [
      {
        required: true,
        message: t('必填'),
        trigger: 'blur',
      },
    ],
    name: [
      {
        required: true,
        message: t('文件不能为空'),
        trigger: 'change',
        validator: (val: string[]) => val.length > 0,
      },
    ],
  };

  /** 操作列表基础方法 */
  const { fetchPackages, handleChangePage, handeChangeLimit, handleConfirmDelete } = useVersionFiles(state, typeParams);

  const { run: runUpdatePackage } = useRequest(updatePackage, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchPackages();
    },
  });

  watch(
    () => state.active,
    (value, old) => {
      if (value && value !== old) {
        state.search = '';
        handleChangePage(1);
        // 大数据类型不需要拉取版本
        if (!isInputType.value) {
          fetchVersions();
        }
      }
    },
    { immediate: true },
  );

  const handleBeforeUpload = async (fileObj: File) => {
    const dbType = props.info.name;
    const pkgType = state.active;
    const { version } = createFileState.formdata;
    const filename = fileObj.name;
    const limitTypes = ['mysql', 'mysql-proxy'];
    if (limitTypes.includes(state.active)) {
      if (!filename.endsWith('tar.gz') && !filename.endsWith('tar.xz')) {
        return;
      }
    }

    const filePath = `/${dbType}/${pkgType}/${version}/${filename}`;
    const tokenResult = await createBkrepoAccessToken({ file_path: filePath });
    const uploadDomain = import.meta.env.MODE === 'production' ? tokenResult.url : '/bkrepo_upload';
    createFileState.uploadUrl = `${uploadDomain}/generic/temporary/upload/${tokenResult.project}/${tokenResult.repo}${tokenResult.path}?token=${tokenResult.token}`;
    return true;
  };

  const getRes = (xhr: XMLHttpRequest): XMLHttpRequestResponseType => {
    const res = xhr.responseText || xhr.response;
    if (!res) {
      return res;
    }

    try {
      return JSON.parse(res);
    } catch {
      return res;
    }
  };

  const handleCustomRequest = (option: UploadRequestOptions) => {
    if (typeof XMLHttpRequest === 'undefined') {
      throw new Error('XMLHttpRequest is undefined');
    }

    const xhr = new XMLHttpRequest();
    const { action } = option;

    if (xhr.upload) {
      xhr.upload.addEventListener('progress', (event) => {
        const progressEvent = event as unknown as UploadProgressEvent;
        progressEvent.percent = event.total > 0 ? (event.loaded / event.total) * 100 : 0;
        option.onProgress(progressEvent);
      });
    }

    xhr.addEventListener('error', () => {
      option.onError(new Error('An error occurred during upload'));
    });

    xhr.addEventListener('load', () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        return option.onError(new Error('An error occurred during upload'));
      }
      option.onSuccess(getRes(xhr));
    });

    xhr.addEventListener('loadend', () => {
      option.onComplete();
    });

    xhr.open(option.method, action, true);

    if (option.withCredentials && 'withCredentials' in xhr) {
      xhr.withCredentials = true;
    }

    if (option.header) {
      if (Array.isArray(option.header)) {
        option.header.forEach((head) => {
          const headerKey = head.name;
          const headerVal = head.value;
          xhr.setRequestHeader(headerKey, headerVal);
        });
      } else {
        const headerKey = option.header.name;
        const headerVal = option.header.value;
        xhr.setRequestHeader(headerKey, headerVal);
      }
    }

    const headers = option.headers || {};
    if (headers instanceof Headers) {
      headers.forEach((value, key) => xhr.setRequestHeader(key, value));
    } else {
      for (const [key, value] of Object.entries(headers)) {
        if (value === null || typeof value === 'undefined') {
          continue;
        }
        xhr.setRequestHeader(key, String(value));
      }
    }

    xhr.send(option.file);
    return xhr;
  };

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

  const handleClearSearch = () => {
    state.search = '';
    handleChangePage(1);
  };

  /**
   * 获取版本号列表
   */
  const fetchVersions = () => {
    createFileState.isLoadVersions = true;
    getVersions(
      {
        query_key: state.active,
        db_type: props.info.name,
      },
      {
        permission: 'catch',
      },
    )
      .then((res) => {
        createFileState.versions = res;
      })
      .finally(() => {
        createFileState.isLoadVersions = false;
      });
  };

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
    Object.assign(createFileState.formdata, file?.data, { path: file?.data.fullPath });
    versionFormRef.value?.clearValidate();
  };

  /**
   * 文件删除
   */
  const handleDeleteFile = () => {
    Object.assign(createFileState.formdata, initCreateFormdata());
  };
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .version-files-file-content {
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

    .bk-tab-content {
      padding: 0;
    }

    .bk-tab-header--active {
      background-color: @bg-white;
    }

    .version-files-table {
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

      &.bk-vxe-table {
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
  }

  .create-new-version-dialog {
    margin-bottom: 16px;

    .bk-button {
      min-width: 64px;
    }

    .bk-upload__tip {
      line-height: normal;
    }
  }
</style>
