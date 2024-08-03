<template>
  <DbSideslider
    v-model:is-show="isShow"
    :title="t('SQL 内容')"
    :width="1100">
    <div style="padding: 20px 25px 0">
      <BkForm
        class="mb-12"
        form-type="vertical">
        <BkFormItem
          :label="t('SQL 来源')"
          required>
          <BkRadioGroup
            v-model="importMode"
            @change="handleImportModeChange">
            <BkRadioButton
              label="manual"
              style="width: 140px">
              {{ t('手动输入') }}
            </BkRadioButton>
            <BkRadioButton
              label="file"
              style="width: 140px">
              {{ t('SQL文件') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
      <KeepAlive>
        <Component
          :is="renderCom"
          ref="fileRef"
          v-model="modelValue"
          @grammar-check="handleGrammarCheck" />
      </KeepAlive>
    </div>
    <template #footer>
      <span
        v-bk-tooltips="{
          ...submitButtonTips,
        }">
        <BkButton
          class="w-88"
          :disabled="!submitButtonTips.disabled"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import LocalFile from './components/local-file/Index.vue';
  import ManualInput from './components/manual-input/Index.vue';

  const { t } = useI18n();

  const comMap = {
    manual: ManualInput,
    file: LocalFile,
  };

  const isShow = defineModel<boolean>('isShow', {
    required: false,
    default: false,
  });

  const importMode = defineModel<keyof typeof comMap>('importMode', {
    required: true,
  });
  const modelValue = defineModel<string[]>('modelValue', {
    required: true,
  });

  const fileRef = ref<InstanceType<typeof LocalFile>>();
  const hasGrammarCheck = ref(false);
  const grammarCheckResult = ref(false);

  const renderCom = computed(() => (isShow.value ? comMap[importMode.value] : 'div'));

  const submitButtonTips = computed(() => {
    const tooltips = {
      content: '',
      disabled: true,
    };

    if (modelValue.value.length < 1) {
      tooltips.content = t('请添加 SQL');
      tooltips.disabled = false;
      return tooltips;
    }

    if (!hasGrammarCheck.value) {
      tooltips.content = t('先执行语法检测');
      tooltips.disabled = false;
      return tooltips;
    }

    if (!grammarCheckResult.value) {
      tooltips.content = t('语法检测失败');
      tooltips.disabled = false;
    }

    return tooltips;
  });

  // 文件来源改变时需要重置文件列表和语法检测
  const handleImportModeChange = () => {
    modelValue.value = [];
  };

  // 语法检测状态
  const handleGrammarCheck = (doCheck: boolean, checkResult: boolean) => {
    hasGrammarCheck.value = doCheck;
    grammarCheckResult.value = checkResult;
  };

  const handleSubmit = () => {
    fileRef.value!.getValue().then((data) => {
      modelValue.value = data;
      isShow.value = false;
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style></style>
