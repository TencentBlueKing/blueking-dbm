<template>
  <RenderTextPlain
    ref="inputRef"
    :rules="rules">
    <BkButton
      text
      theme="primary"
      @click="handleShowSql">
      {{ modelValue.length < 1 ? t('点击添加') : t('n 个 SQL 文件', { n: modelValue.length }) }}
    </BkButton>
  </RenderTextPlain>
  <SqlContent
    v-model="modelValue"
    v-model:importMode="importMode"
    v-model:is-show="isShowSql" />
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import type { ComponentExposed, ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RenderTextPlain from '@components/render-table/columns/text-plain/index.vue';

  import SqlContent from './components/sql-content/Index.vue';

  interface Expose {
    getValue: () => Promise<{
      sql_files: string[];
    }>;
  }

  const { t } = useI18n();

  const importMode = defineModel<ComponentProps<typeof SqlContent>['importMode']>('importMode', {
    required: true,
  });

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const rules = [
    {
      validator: () => modelValue.value.length > 0,
      message: t('执行的 SQL 不能为空'),
    },
  ];

  const inputRef = ref<ComponentExposed<typeof RenderTextPlain>>();
  const isShowSql = ref(false);

  const handleShowSql = () => {
    isShowSql.value = true;
  };

  defineExpose<Expose>({
    getValue: () =>
      inputRef.value!.getValue().then(() => ({
        sql_files: modelValue.value,
      })),
  });
</script>
