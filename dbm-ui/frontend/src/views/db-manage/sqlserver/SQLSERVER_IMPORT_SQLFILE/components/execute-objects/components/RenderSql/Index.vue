<template>
  <EditableColumn
    ref="sqlFileColumnRef"
    :append-rules="rules"
    field="sql_files"
    :label="t('执行的 SQL')"
    :width="300">
    <EditableBlock>
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
          <span v-else-if="modelValue.length === 1">{{ getSQLFilename(modelValue[0] || '') }}</span>
          <span v-else>{{ t('n 个 SQL 文件', { n: modelValue.length }) }}</span>
        </BkButton>
      </span>
    </EditableBlock>
  </EditableColumn>
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { getSQLFilename } from '@utils';

  import SqlContent from './components/sql-content/Index.vue';

  interface Props {
    clusterVersionList: string[];
    dbNames: string[];
    ignoreDbNames: string[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });
  const importMode = defineModel<ComponentProps<typeof SqlContent>['importMode']>('importMode', {
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('执行的 SQL 不能为空'),
      trigger: 'change',
      validator: () => modelValue.value.length > 0,
    },
  ];

  const sqlFileColumnRef = useTemplateRef('sqlFileColumnRef');

  const isShowSql = ref(false);

  const actionTips = computed(() => (props.clusterVersionList.length < 1 ? t('请先选择目标集群') : ''));

  watch(isShowSql, () => {
    nextTick(() => {
      if (!isShowSql.value) {
        sqlFileColumnRef.value!.validate();
      }
    });
  });

  const handleShowSql = () => {
    isShowSql.value = true;
  };
</script>
