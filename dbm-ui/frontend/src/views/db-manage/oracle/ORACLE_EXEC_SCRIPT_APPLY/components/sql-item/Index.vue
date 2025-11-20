<template>
  <BkFormItem
    :label="t('SQL 来源')"
    property="importMode"
    required
    :rules="rules">
    <BkRadioGroup
      v-model="importMode"
      class="mb-12"
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
    <KeepAlive>
      <Component
        :is="renderCom"
        ref="fileRef"
        v-model="modelValue"
        v-bind="attrs"
        :cluster-version-list="clusterVersionList"
        @grammar-check="handleGrammarCheck" />
    </KeepAlive>
  </BkFormItem>
</template>
<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import LocalFile from './components/local-file/Index.vue';
  import ManualInput from './components/manual-input/Index.vue';

  interface Props {
    clusterVersionList: string[];
  }

  interface Expose {
    getValue: () => Promise<{
      script_files: string[];
    }>;
  }

  defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });
  const importMode = defineModel<'manual' | 'file'>('importMode', {
    required: true,
  });

  const { t } = useI18n();

  const comMap = {
    file: LocalFile,
    manual: ManualInput,
  };

  const attrs = useAttrs();

  const fileRef = ref<InstanceType<typeof LocalFile>>();
  const hasGrammarCheck = ref(false);
  const grammarCheckResult = ref(false);

  const renderCom = computed(() => comMap[importMode.value]);

  const rules = [
    {
      message: t('请添加 SQL'),
      require: true,
      validator: (value: UnwrapRef<typeof modelValue>) => value.length > 0,
    },
    {
      message: t('先执行语法检测'),
      require: true,
      validator: () => hasGrammarCheck.value,
    },
    {
      message: t('语法检测失败'),
      require: true,
      validator: () => grammarCheckResult.value,
    },
  ];

  // 文件来源改变时需要重置文件列表和语法检测
  const handleImportModeChange = () => {
    modelValue.value = [];
  };

  // 语法检测状态
  const handleGrammarCheck = (doCheck: boolean, checkResult: boolean) => {
    hasGrammarCheck.value = doCheck;
    grammarCheckResult.value = checkResult;
  };

  defineExpose<Expose>({
    getValue() {
      return fileRef.value!.getValue();
    },
  });
</script>
