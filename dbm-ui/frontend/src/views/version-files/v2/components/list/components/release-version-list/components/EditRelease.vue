<template>
  <DbSideslider
    v-model:is-show="isShow"
    :cancel-text="t('取消')"
    class="edit-release-slider-main"
    :confirm-handler="handleSubmit"
    :confirm-text="t('确定')"
    render-directive="if"
    :width="640">
    <template #header>
      <div class="header-main">
        <span>{{ props.isEdit ? t('编辑发行版') : t('新增发行版') }}</span>
        <BkTag theme="info">{{ tagLabel }}</BkTag>
      </div>
    </template>
    <div class="content-main">
      <DbForm
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
      </DbForm>
    </div>
  </DbSideslider>
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

  const formRules = computed(() => ({
    name: [
      {
        message: t('请勿使用中文'),
        trigger: 'blur',
        validator: (value: string) => props.isEdit || !/[\u4e00-\u9fa5]/.test(value),
      },
      {
        message: t('格式不正确，请勿使用空格或特殊符号'),
        trigger: 'blur',
        validator: (value: string) => props.isEdit || /^[A-Za-z0-9_.-]+$/.test(value),
      },
      {
        message: t('该发行版名已存在'),
        trigger: 'blur',
        validator: (value: string) => props.isEdit || !props.existedNameList.includes(value.toLocaleLowerCase()),
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

  const { runAsync: runCreateReleaseVersion } = useRequest(createReleaseVersion, {
    manual: true,
    onSuccess() {
      emits('success');
      messageSuccess(t('操作成功'));
    },
  });

  const { runAsync: runUpdateReleaseVersion } = useRequest(updateReleaseVersion, {
    manual: true,
    onSuccess() {
      emits('success');
      messageSuccess(t('操作成功'));
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

  const handleSubmit = async () => {
    await formRef.value.validate();
    const commonParams = {
      db_type: props.dbType,
      engine: formModel.value.engine,
      name: formModel.value.name,
      pkg_type: props.pkgType,
    };
    if (props.isEdit) {
      return runUpdateReleaseVersion({
        ...commonParams,
        id: props.data!.id,
      });
    }
    return runCreateReleaseVersion(commonParams);
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
