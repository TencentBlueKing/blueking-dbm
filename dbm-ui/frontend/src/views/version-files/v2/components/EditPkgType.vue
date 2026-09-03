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
  <BkDialog
    v-model:is-show="isShow"
    class="edit-pkg-type-dialog"
    quick-close
    render-directive="if"
    :title="isEdit ? t('编辑包类型') : t('新建包类型')"
    :width="480">
    <BkForm
      ref="formRef"
      class="edit-pkg-type-form"
      form-type="vertical"
      :model="formModel"
      :rules="formRules"
      @validate="handleFormValidate">
      <BkFormItem
        :class="{ 'is-hide-tip': !formModel.value }"
        :label="t('标识')"
        property="value"
        required>
        <BkInput
          v-model="formModel.value"
          :disabled="isEdit"
          :placeholder="t('请输入xx', [t('标识')])" />
        <div
          v-if="!hideTipMap.value && !isEdit"
          class="edit-pkg-type-form-desc">
          {{ t('仅支持字母、数字、连字符、下划线、点号，创建后不可改') }}
        </div>
      </BkFormItem>
      <BkFormItem
        :class="{ 'is-hide-tip': !formModel.name, 'mt-32': !isEdit }"
        :label="t('显示名')"
        property="name"
        required>
        <BkInput
          v-model="formModel.name"
          :placeholder="t('请输入xx', [t('显示名')])" />
        <div
          v-if="!hideTipMap.name"
          class="edit-pkg-type-form-desc">
          {{ t('支持中文、字母、数字、连字符、下划线、点号，创建后可修改') }}
        </div>
      </BkFormItem>
      <BkFormItem
        class="mt-32"
        :label="t('版本号位数')"
        property="version_num"
        required>
        <BkRadioGroup
          v-model="formModel.version_num"
          :disabled="isVersionNumDisabled">
          <BkRadio
            v-for="item in versionDigitOptions"
            :key="item.value"
            :label="item.value">
            {{ item.label }}
          </BkRadio>
        </BkRadioGroup>
        <div
          v-if="isEdit && data?.related_versions && data.related_versions > 0"
          class="edit-pkg-type-form-desc is-last-tip">
          {{ t('已有 n 个版本，位数不可修改', { n: data?.related_versions || 0 }) }}
        </div>
        <div
          v-if="!isEdit"
          class="edit-pkg-type-form-desc is-last-tip">
          {{ t('添加版本后将锁定位数，清空版本后可重新选择') }}
        </div>
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
      <BkButton
        class="ml-8"
        :loading="updateLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updatePkgType } from '@services/source/version';

  import { messageSuccess } from '@utils';

  import { CHINESE_CHAR_REG, IDENTIFIER_NAME_REG } from '../common';

  interface Props {
    data?: {
      name: string;
      related_distributions: number;
      related_versions: number;
      value: string;
      version_num: number;
    };
    dbType: string;
    isEdit: boolean;
    totalList: NonNullable<Props['data']>[];
  }

  type Emits = (e: 'success', data?: typeof formModel.value) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const formRef = ref();
  const formModel = ref({
    name: '',
    value: '',
    version_num: 3,
  });
  const hideTipMap = ref({
    name: false,
    value: false,
  });

  const versionDigitOptions = [
    {
      label: t('3 位 (如 5.0.14)'),
      value: 3,
    },
    {
      label: t('6 位 (如 8.0.30.1.0.0)'),
      value: 6,
    },
  ];

  const isVersionNumDisabled = computed(() => props.isEdit && (props.data?.related_versions ?? 0) > 0);

  const formRules = computed(() => ({
    name: [
      {
        message: t('格式不正确，请勿使用括号或特殊符号'),
        trigger: 'blur',
        validator: (value: string) => /^[\u4e00-\u9fff\u3400-\u4dbf0-9A-Za-z._-\s]+$/.test(value),
      },
    ],
    value: [
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
        message: t('该数据库类型下已存在同名标识'),
        trigger: 'blur',
        validator: (value: string) => {
          if (props.isEdit) {
            return true;
          }
          return !props.totalList.some((item) => item.value.toLocaleLowerCase() === value.toLocaleLowerCase());
        },
      },
    ],
  }));

  const { loading: updateLoading, run: runUpdatePkgType } = useRequest(updatePkgType, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      messageSuccess(t('操作成功'));
      emits('success', !props.isEdit ? formModel.value : undefined);
    },
  });

  watch(isShow, (show) => {
    if (!show) {
      return;
    }
    formModel.value = {
      name: props.data?.name || '',
      value: props.data?.value || '',
      version_num: props.data?.version_num || 3,
    };
  });

  const handleSubmit = async () => {
    await formRef.value.validate();
    const items = props.totalList.reduce<Props['totalList']>((acc, item) => {
      if (item.value !== formModel.value.value) {
        acc.push({
          name: item.name,
          related_distributions: item.related_distributions,
          related_versions: item.related_versions,
          value: item.value,
          version_num: item.version_num,
        });
      } else {
        acc.push({
          name: formModel.value.name,
          related_distributions: item.related_distributions,
          related_versions: item.related_versions,
          value: formModel.value.value,
          version_num: formModel.value.version_num,
        });
      }
      return acc;
    }, []);
    if (!props.isEdit) {
      items.push({
        name: formModel.value.name,
        related_distributions: 0,
        related_versions: 0,
        value: formModel.value.value,
        version_num: formModel.value.version_num,
      });
    }
    runUpdatePkgType({
      db_type: props.dbType,
      items,
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };

  const handleFormValidate = (property: string, result: boolean) => {
    hideTipMap.value[property as keyof typeof hideTipMap.value] =
      !result && !!formModel.value[property as keyof typeof formModel.value];
  };
</script>

<style lang="less">
  .edit-pkg-type-dialog {
    .edit-pkg-type-form-desc {
      position: absolute;
      top: 34px;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;

      &.is-last-tip {
        margin-top: -6px;
      }
    }

    .edit-pkg-type-form {
      .is-hide-tip {
        .bk-form-error {
          display: none;
        }
      }
    }
  }
</style>
