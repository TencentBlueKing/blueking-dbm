<template>
  <DbSideslider
    v-model:is-show="isShow"
    render-directive="show"
    :width="1100">
    <template #header>
      <span>{{ t('SQL 内容') }}</span>
      <span>
        <slot name="header" />
      </span>
    </template>
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
          v-model="localModelValue"
          v-bind="attrs"
          :cluster-version-list="clusterVersionList"
          :is-show="isShow"
          @grammar-check="handleGrammarCheck" />
      </KeepAlive>
    </div>
    <template #footer>
      <span
        v-bk-tooltips="{
          content: submitButtonTips,
          disabled: !submitButtonTips,
        }">
        <BkButton
          class="w-88"
          :disabled="Boolean(submitButtonTips)"
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
  import { ref, type UnwrapRef, useAttrs, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import LocalFile from './components/local-file/Index.vue';
  import ManualInput from './components/manual-input/Index.vue';

  interface Props {
    clusterVersionList: string[];
  }

  defineProps<Props>();

  const { t } = useI18n();

  const comMap = {
    manual: ManualInput,
    file: LocalFile,
  };

  const isShow = defineModel<boolean>('isShow', {
    required: false,
    default: false,
  });

  const importMode = defineModel<'manual' | 'file'>('importMode', {
    required: true,
  });
  const modelValue = defineModel<string[]>('modelValue', {
    required: true,
  });

  const attrs = useAttrs();

  const fileRef = ref<InstanceType<typeof LocalFile>>();
  const localModelValue = ref<UnwrapRef<typeof modelValue>>([]);
  const hasGrammarCheck = ref(false);
  const grammarCheckResult = ref(false);

  const renderCom = computed(() => comMap[importMode.value]);

  const submitButtonTips = computed(() => {
    if (localModelValue.value.length < 1) {
      return t('请添加 SQL');
    }

    if (!hasGrammarCheck.value) {
      return t('先执行语法检测');
    }
    if (!grammarCheckResult.value) {
      return t('语法检测失败');
    }

    return '';
  });

  let isInnerChange = false;
  watch(
    modelValue,
    () => {
      if (isInnerChange) {
        isInnerChange = false;
        return;
      }
      localModelValue.value = modelValue.value;
    },
    {
      immediate: true,
    },
  );

  // 文件来源改变时需要重置文件列表和语法检测
  const handleImportModeChange = () => {
    localModelValue.value = [];
  };

  // 语法检测状态
  const handleGrammarCheck = (doCheck: boolean, checkResult: boolean) => {
    hasGrammarCheck.value = doCheck;
    grammarCheckResult.value = checkResult;
  };

  const handleSubmit = () => {
    fileRef.value!.getValue().then((data) => {
      isInnerChange = true;
      modelValue.value = data;
      isShow.value = false;
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
