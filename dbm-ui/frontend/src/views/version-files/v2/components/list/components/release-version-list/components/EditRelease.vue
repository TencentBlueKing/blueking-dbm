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
        :rules="formRules">
        <BkFormItem
          :label="t('发行版名称')"
          property="name"
          required>
          <BkInput
            v-model="formModel.name"
            :placeholder="t('请输入发行版名称，如：TXSQL，以英文字母开头，且只能包含英文字母、数字、连字符-')" />
        </BkFormItem>
        <BkFormItem
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

  import { messageSuccess } from '@utils';

  interface Props {
    data?: ReleaseVersionModel;
    dbType: string;
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
      messageSuccess(t('新增成功'));
      isShow.value = false;
    },
  });

  const { loading: updateLoading, run: runUpdateReleaseVersion } = useRequest(updateReleaseVersion, {
    manual: true,
    onSuccess() {
      emits('success');
      messageSuccess(t('更新成功'));
      isShow.value = false;
    },
  });

  const formRules = {
    name: [
      {
        message: t('以英文字母开头，且只能包含英文字母、数字、连字符-'),
        trigger: 'blur',
        validator: (value: string) => /^[a-zA-Z][a-zA-Z0-9-]*$/.test(value),
      },
    ],
  };

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
    }
  }
</style>
