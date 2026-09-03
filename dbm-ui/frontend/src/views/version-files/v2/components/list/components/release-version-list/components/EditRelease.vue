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
    class="edit-release-slider-main"
    render-directive="if"
    :width="640">
    <template #header>
      <div class="header-main">
        <span>{{ props.isEdit ? t('编辑发行版') : t('新增发行版') }}</span>
        <BkTag theme="info">{{ tagLabel }}</BkTag>
      </div>
    </template>
    <div class="content-main">
      <BkForm
        ref="formRef"
        class="mt-14"
        form-type="vertical"
        :model="formModel"
        :rules="formRules"
        @validate="handleFormValidate">
        <BkFormItem
          :class="{ 'is-hide-tip': !formModel.name }"
          :label="t('发行版名称')"
          property="name"
          required>
          <BkInput
            v-model="formModel.name"
            clearable
            :disabled="!!data?.version_series_count"
            :maxlength="50"
            :placeholder="t('请输入xx', [t('发行版名称')])"
            show-word-limit />
          <div
            v-if="!hideNameTip && !isEdit"
            class="item-tip">
            {{ t('仅支持字母、数字、连字符、下划线、点号，创建后不可修改') }}
          </div>
        </BkFormItem>
        <BkFormItem
          :class="{ 'mt-32': !isEdit }"
          property="engine"
          required>
          <template #label>
            <span>{{ t('存储引擎') }}</span>
            <span class="engine-tip">({{ t('发行版若无存储引擎要求，请选择无') }})</span>
          </template>
          <BkSelect v-model="formModel.engine">
            <BkOption
              v-for="item in engineList"
              :key="item.value"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
        </BkFormItem>
      </BkForm>
      <div class="operate-main">
        <BkButton
          class="operate-button"
          :loading="createLoading || updateLoading"
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
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { createReleaseVersion, getMysqlEngineList, updateReleaseVersion } from '@services/source/version';

  import { CHINESE_CHAR_REG, IDENTIFIER_NAME_REG } from '@views/version-files/v2/common';

  import { messageSuccess } from '@utils';

  interface Props {
    data?: ReleaseVersionModel;
    dbType: string;
    existedNameList: string[];
    isEdit?: boolean;
    pkgType: string;
    tagLabel: string;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isEdit: false,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const formRef = ref();
  const formModel = ref({
    engine: 'default',
    name: '',
  });
  const engineList = ref<
    {
      label: string;
      value: string;
    }[]
  >([]);
  const hideNameTip = ref(false);

  /** 编辑时名称没有改动：存量数据可能不符合当前命名规则，不做拦截，也不算重名 */
  const isNameUnchanged = (value: string) => props.data?.name.toLocaleLowerCase() === value.toLocaleLowerCase();

  const formRules = computed(() => ({
    name: [
      {
        message: t('请勿使用中文'),
        trigger: 'blur',
        validator: (value: string) => isNameUnchanged(value) || !CHINESE_CHAR_REG.test(value),
      },
      {
        message: t('格式不正确，请勿使用空格或特殊符号'),
        trigger: 'blur',
        validator: (value: string) => isNameUnchanged(value) || IDENTIFIER_NAME_REG.test(value),
      },
      {
        message: t('该发行版名已存在'),
        trigger: 'blur',
        validator: (value: string) =>
          isNameUnchanged(value) || !props.existedNameList.includes(value.toLocaleLowerCase()),
      },
    ],
  }));

  useRequest(getMysqlEngineList, {
    onSuccess(data) {
      engineList.value = [
        {
          label: t('无'),
          value: 'default',
        },
        ...data.map((item) => ({
          label: item,
          value: item,
        })),
      ];
    },
  });

  const { loading: createLoading, run: runCreateReleaseVersion } = useRequest(createReleaseVersion, {
    manual: true,
    onSuccess() {
      emits('success');
      messageSuccess(t('操作成功'));
      isShow.value = false;
    },
  });

  const { loading: updateLoading, run: runUpdateReleaseVersion } = useRequest(updateReleaseVersion, {
    manual: true,
    onSuccess() {
      emits('success');
      messageSuccess(t('操作成功'));
      isShow.value = false;
    },
  });

  watch(
    () => props.data,
    () => {
      if (props.data) {
        formModel.value.engine = props.data.engine;
        formModel.value.name = props.data.name;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    isShow,
    () => {
      if (!isShow.value) {
        formModel.value = {
          engine: 'default',
          name: '',
        };
      }
    },
    {
      immediate: true,
    },
  );

  const handleFormValidate = (property: string, result: boolean) => {
    if (property === 'name') {
      hideNameTip.value = !result && !!formModel.value.name;
    }
  };

  const handleSubmit = () => {
    formRef.value.validate().then(() => {
      const commonParams = {
        db_type: props.dbType,
        engine: formModel.value.engine,
        name: formModel.value.name,
        pkg_type: props.pkgType,
      };
      if (props.isEdit) {
        runUpdateReleaseVersion({
          ...commonParams,
          id: props.data!.id,
        });
      } else {
        runCreateReleaseVersion(commonParams);
      }
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .edit-release-slider-main {
    .header-main {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .content-main {
      padding: 0 24px;
      font-family: 'Microsoft YaHei', Arial, sans-serif;

      .operate-main {
        display: flex;
        gap: 8px;
        margin-top: 32px;

        .operate-button {
          width: 88px;
        }
      }

      .engine-tip {
        position: absolute;
        left: 64px;
        color: #979ba5;
      }

      .is-hide-tip {
        .bk-form-error {
          display: none;
        }
      }

      .item-tip {
        position: absolute;
        top: 28px;
        font-size: 12px;
        color: #979ba5;
      }
    }
  }
</style>
