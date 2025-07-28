<template>
  <BkFormItem
    :label="t('SQL 来源')"
    required>
    <BkRadioGroup
      v-model="importMode"
      class="mb-8"
      :disabled="disabled"
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
        :disabled="disabled"
        :execute-objects="executeObjects"
        :is-show="isShow"
        @grammar-check="handleGrammarCheck" />
    </KeepAlive>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type SqlFile from '@views/db-manage/common/mysql-sql-execute/model/SqlFile';

  import LocalFile from './components/local-file/Index.vue';
  import ManualInput from './components/manual-input/Index.vue';

  interface Props {
    clusterVersionList: string[];
    dbNames: string[];
    ignoreDbnames: string[];
  }

  interface Expose {
    getFileData: () => Record<string, SqlFile>;
    setInit: (cacheData: Record<string, SqlFile>) => void;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });
  const importMode = defineModel<'manual' | 'file'>('importMode', {
    required: true,
  });
  const hasGrammarCheck = defineModel<boolean>('hasGrammarCheck', {
    required: true,
  });
  const grammarCheckResult = defineModel<boolean>('grammarCheckResult', {
    required: true,
  });

  const { t } = useI18n();

  const comMap = {
    file: LocalFile,
    manual: ManualInput,
  };

  const attrs = useAttrs();

  const fileRef = ref<InstanceType<typeof LocalFile>>();
  const isShow = ref(true);

  const disabled = computed(() => props.dbNames.length === 0);
  const renderCom = computed(() => comMap[importMode.value]);

  const executeObjects = computed(() => {
    return [
      {
        dbnames: props.dbNames,
        ignore_dbnames: props.ignoreDbnames,
        line_id: 1,
        // sql_files: modelValue.value,
      },
    ];
  });

  watch(
    () => [props.dbNames, props.ignoreDbnames],
    () => {
      fileRef.value!.setStateToUncheck();
    },
  );

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
    getFileData() {
      return fileRef.value!.getFileData();
    },
    setInit(cacheData: Record<string, SqlFile>) {
      fileRef.value!.setInit(cacheData);
    },
  });
</script>
