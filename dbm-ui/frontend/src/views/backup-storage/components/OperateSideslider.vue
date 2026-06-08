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
  <DbSideslider
    v-model:is-show="isShow"
    :title="isEditMode ? t('编辑配置') : t('新增配置')"
    :width="640">
    <template #header>
      <div class="header-title">
        <span>{{ isEditMode ? t('编辑配置') : t('新增配置') }}</span>
        <span
          v-if="isEditMode"
          class="sideslider-sub-title">
          {{ editingData!.bk_cloud_name }}[{{ editingData!.bk_cloud_id }}]
        </span>
      </div>
    </template>
    <BkForm
      ref="formRef"
      class="backup-config-form"
      form-type="vertical"
      :model="formData"
      :rules="formRules">
      <template v-if="!isEditMode">
        <BkFormItem
          :label="t('云区域')"
          property="bk_cloud_id"
          required>
          <BkSelect
            v-model="formData.bk_cloud_id"
            filterable
            :input-search="false"
            :loading="cloudLoading"
            :placeholder="t('请选择云区域')">
            <BkOption
              v-for="item in cloudList"
              :key="item.bk_cloud_id"
              :disabled="existingCloudIds.includes(item.bk_cloud_id)"
              :label="`${item.bk_cloud_name}[${item.bk_cloud_id}]`"
              :value="item.bk_cloud_id">
              <template #default>
                <div class="cloud-option">
                  <span>{{ item.bk_cloud_name }}[{{ item.bk_cloud_id }}]</span>
                  <BkTag
                    v-if="existingCloudIds.includes(item.bk_cloud_id)"
                    class="ml-auto"
                    size="small"
                    theme=""
                    type="filled">
                    {{ t('已配置') }}
                  </BkTag>
                </div>
              </template>
            </BkOption>
          </BkSelect>
        </BkFormItem>
        <hr class="form-divider" />
      </template>

      <BkFormItem
        label="Region"
        property="region"
        required>
        <BkInput
          v-model="formData.region"
          :placeholder="t('如 ap-guangzhou')" />
      </BkFormItem>

      <BkFormItem
        label="Endpoint"
        property="endpoint"
        required>
        <BkInput
          v-model="formData.endpoint"
          :placeholder="t('如 cos.ap-guangzhou.myqcloud.com')" />
      </BkFormItem>

      <BkFormItem
        label="SecretId"
        property="secret_id"
        required>
        <BkInput
          v-model="formData.secret_id"
          :placeholder="t('请输入')"
          :type="showSecretId ? 'text' : 'password'">
          <template #suffix>
            <DbIcon
              class="password-toggle-icon"
              :type="showSecretId ? 'eye' : 'eye-slash'"
              @click="showSecretId = !showSecretId" />
          </template>
        </BkInput>
      </BkFormItem>

      <BkFormItem
        label="SecretKey"
        property="secret_key"
        required>
        <BkInput
          v-model="formData.secret_key"
          :placeholder="t('请输入')"
          :type="showSecretKey ? 'text' : 'password'">
          <template #suffix>
            <DbIcon
              class="password-toggle-icon"
              :type="showSecretKey ? 'eye' : 'eye-slash'"
              @click="showSecretKey = !showSecretKey" />
          </template>
        </BkInput>
      </BkFormItem>

      <BkFormItem
        label="Bucket"
        property="bucket_name"
        required>
        <BkInput
          v-model="formData.bucket_name"
          :placeholder="t('存储桶名称')" />
      </BkFormItem>

      <BkFormItem
        :label="t('存储类型')"
        property="storage_type"
        required>
        <BkSelect
          v-model="formData.storage_type"
          :clearable="false"
          :placeholder="t('请选择存储类型')">
          <BkOption
            v-for="item in storageTypeOptions"
            :key="item"
            :label="item"
            :value="item" />
        </BkSelect>
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        class="w-88"
        :loading="submitLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { type BackupConfigRow, upsertCommonLevelConfig } from '@services/source/configs';
  import { getCloudList } from '@services/source/ipchooser';

  import { messageSuccess } from '@utils';

  interface Props {
    data?: BackupConfigRow | null;
    existingCloudIds?: number[];
  }

  type Emits = (e: 'saved') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: null,
    existingCloudIds: () => [],
  });

  const emit = defineEmits<Emits>();

  const isShow = defineModel<boolean>('show', {
    default: false,
  });
  const { t } = useI18n();

  const isEditMode = computed(() => !!props.data);
  const editingData = computed(() => props.data);

  const formRef = ref();
  const showSecretId = ref(false);
  const showSecretKey = ref(false);
  const submitLoading = ref(false);

  const storageTypeOptions = computed(() => {
    const base = ['cos', 's3', 'bkrepo'];
    if (formData.bk_cloud_id === 0 || formData.bk_cloud_id === '0') {
      return [...base, 'hdfs'];
    }
    return base;
  });

  const { data: cloudList, loading: cloudLoading } = useRequest(getCloudList, {
    initialData: [],
  });

  // 从 conf_items 中取值
  const getConfValue = (confItems: BackupConfigRow['conf_items'], confName: string) => {
    const item = confItems.find((i) => i.conf_name === confName);
    return item?.conf_value || '';
  };

  // 表单数据
  const formData = reactive({
    bk_cloud_id: '' as number | string,
    bucket_name: '',
    endpoint: '',
    region: '',
    secret_id: '',
    secret_key: '',
    storage_type: 'cos',
  });

  // 表单字段与 conf_name 的映射
  const confKeyMap: Record<string, string> = {
    bucket_name: 'cos_auth.bucket_name',
    endpoint: 'cos_auth.endpoint',
    region: 'cos_auth.region',
    secret_id: 'cos_auth.secret_id',
    secret_key: 'cos_auth.secret_key',
    storage_type: 'cos_auth.storage_type',
  };

  // 初始化表单数据
  const initFormData = () => {
    if (isEditMode.value && editingData.value) {
      formData.bk_cloud_id = editingData.value.bk_cloud_id;
      Object.entries(confKeyMap).forEach(([key, confName]) => {
        (formData as any)[key] =
          getConfValue(editingData.value!.conf_items, confName) || (key === 'storage_type' ? 'cos' : '');
      });
    } else {
      Object.assign(formData, {
        bk_cloud_id: '',
        bucket_name: '',
        endpoint: '',
        region: '',
        secret_id: '',
        secret_key: '',
        storage_type: 'cos',
      });
    }
    showSecretId.value = false;
    showSecretKey.value = false;
  };

  // 表单验证规则
  const formRules = {
    bk_cloud_id: [
      {
        message: t('请选择云区域'),
        required: true,
        trigger: 'change',
        validator: (value: number | string) => value !== '' && value !== undefined,
      },
    ],
    bucket_name: [
      {
        message: t('请输入 Bucket'),
        required: true,
        trigger: 'blur',
      },
    ],
    endpoint: [
      {
        message: t('请输入 Endpoint'),
        required: true,
        trigger: 'blur',
      },
    ],
    region: [
      {
        message: t('请输入 Region'),
        required: true,
        trigger: 'blur',
      },
    ],
    secret_id: [
      {
        message: t('请输入 SecretId'),
        required: true,
        trigger: 'blur',
      },
    ],
    secret_key: [
      {
        message: t('请输入 SecretKey'),
        required: true,
        trigger: 'blur',
      },
    ],
    storage_type: [
      {
        message: t('请选择存储类型'),
        required: true,
        trigger: 'change',
      },
    ],
  };

  // 监听侧滑面板打开，初始化表单
  watch(
    isShow,
    (val) => {
      if (val) {
        initFormData();
        nextTick(() => {
          formRef.value?.clearValidate();
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 取消 — 关闭侧滑
  const handleCancel = () => {
    isShow.value = false;
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      submitLoading.value = true;
      await formRef.value?.validate();
      await upsertCommonLevelConfig({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        conf_items: [
          { conf_name: 'cos_auth.region', conf_value: formData.region, op_type: 'update' as const },
          { conf_name: 'cos_auth.endpoint', conf_value: formData.endpoint, op_type: 'update' as const },
          { conf_name: 'cos_auth.secret_id', conf_value: formData.secret_id, op_type: 'update' as const },
          { conf_name: 'cos_auth.secret_key', conf_value: formData.secret_key, op_type: 'update' as const },
          { conf_name: 'cos_auth.bucket_name', conf_value: formData.bucket_name, op_type: 'update' as const },
          { conf_name: 'cos_auth.storage_type', conf_value: formData.storage_type, op_type: 'update' as const },
        ],
        conf_type: 'backup_client',
        level_name: 'bk_cloud_id',
        level_value: Number(formData.bk_cloud_id),
        meta_cluster_type: 'common',
        version: 'cosinfo.toml',
      });
      messageSuccess(isEditMode.value ? t('保存成功') : t('新增成功'));
      emit('saved');
    } finally {
      submitLoading.value = false;
    }
  };
</script>

<style lang="less" scoped>
  .sideslider-sub-title {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-size: 14px;
    font-weight: normal;
    color: #979ba5;

    &::before {
      position: absolute;
      top: 50%;
      left: 0;
      width: 1px;
      height: 14px;
      content: '';
      background: #dcdee5;
      transform: translateY(-50%);
    }
  }

  .backup-config-form {
    padding: 24px;

    .form-divider {
      border: none;
      border-top: 1px solid #dcdee5;
      margin: 4px 0 20px;
    }

    .cloud-text {
      font-size: 13px;
      color: #313238;
      line-height: 32px;
    }

    .cloud-option {
      display: flex;
      align-items: center;
      width: 100%;
    }

    .password-toggle-icon {
      cursor: pointer;
      color: #979ba5;
      font-size: 14px;

      &:hover {
        color: #3a84ff;
      }
    }
  }
</style>
