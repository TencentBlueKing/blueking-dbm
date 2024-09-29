<template>
  <RenderTextPlain
    ref="inputRef"
    :rules="rules">
    <span
      v-bk-tooltips="{
        content: actionTips,
        disabled: !actionTips,
      }">
      <BkButton
        :disabled="Boolean(actionTips)"
        text
        theme="primary"
        @click="handleShowSql">
        <span v-if="modelValue.length < 1">{{ t('点击添加') }}</span>
        <span v-else-if="modelValue.length === 1">{{ modelValue[0] }}</span>
        <span v-else>{{ t('n 个 SQL 文件', { n: modelValue.length }) }}</span>
      </BkButton>
    </span>
  </RenderTextPlain>
  <SqlContent
    v-model="modelValue"
    v-model:import-mode="importMode"
    v-model:is-show="isShowSql"
    :cluster-version-list="clusterVersionList">
    <template #header>
      <span style="margin-left: 30px; font-size: 12px; font-weight: normal; color: #63656e">
        <span>{{ t('变更的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in dbNames"
            :key="item">
            {{ item }}
          </BkTag>
          <template v-if="dbNames.length < 1">--</template>
        </span>
        <span class="ml-25">{{ t('忽略的 DB:') }}</span>
        <span class="ml-4">
          <BkTag
            v-for="item in ignoreDbNames"
            :key="item">
            {{ item }}
          </BkTag>
          <template v-if="ignoreDbNames.length < 1">--</template>
        </span>
      </span>
    </template>
  </SqlContent>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import type { ComponentExposed, ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RenderTextPlain from '@components/render-table/columns/text-plain/index.vue';

  import SqlContent from './components/sql-content/Index.vue';

  interface Props {
    clusterVersionList: string[];
    dbNames: string[];
    ignoreDbNames: string[];
  }

  interface Expose {
    getValue: () => Promise<{
      sql_files: string[];
    }>;
  }

  const props = defineProps<Props>();

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

  const actionTips = computed(() => (props.clusterVersionList.length < 1 ? t('请先选择目标集群') : ''));

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
