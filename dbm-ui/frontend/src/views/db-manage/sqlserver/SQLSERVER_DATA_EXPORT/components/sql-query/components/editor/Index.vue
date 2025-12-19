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
  <div
    ref="rootRef"
    class="sql-execute-editor"
    :class="{ 'is-full-screen': isFullscreen }">
    <div class="editor-layout-header">
      <div>{{ t('SQL 查询') }}</div>
      <div class="query-operation-main">
        <div
          v-for="item in operationList"
          :key="item.value"
          class="operation-item"
          :class="{ 'operation-item-active': currentOperation === item.value }"
          @click="() => handleChangeOperation(item.value)">
          <DbIcon
            style="font-size: 14px"
            :type="item.icon" />
          <span class="ml-4">{{ item.name }}</span>
        </div>
      </div>
      <div class="editro-action-box">
        <CodeFormat
          :data="modelValue"
          @format="handleCodeFormat" />
        <FontSetting @change="handleChangeFontSize" />
        <FullScreen @change="handleChangeFullScreen" />
      </div>
    </div>
    <BkResizeLayout
      :border="false"
      class="editor-main-resizer"
      :initial-divide="divideMin"
      :max="800"
      :min="divideMin"
      placement="right"
      style="height: 100%"
      @after-resize="handleAfterResize">
      <template #aside>
        <FrequentQuery
          v-if="currentOperation === 'query'"
          @choose-sql="handleChooseSql" />
        <MyCollection
          v-if="currentOperation === 'collect'"
          :key="collectionRenderKey"
          :sql-profile="sqlProfile"
          @change="fetchProfileSql"
          @choose-sql="handleChooseSql" />
      </template>
      <template #main>
        <div
          ref="editorRef"
          style="height: calc(100% - 95px)" />
        <div class="editor-operate-main">
          <BkPopConfirm
            :title="t('收藏')"
            trigger="click"
            width="340"
            @confirm="handleClickCollect">
            <template #content>
              <div class="editor-collect-main">
                <div class="collect-title">
                  {{ t('名称') }}
                </div>
                <AutoFocusInput
                  v-model="collectName"
                  class="mt-6 mb-18" />
              </div>
            </template>
            <BkButton
              class="collect-btn"
              :disabled="!modelValue"
              outline>
              <DbIcon
                class="mr-5"
                type="star" />
              {{ t('收藏') }}
            </BkButton>
          </BkPopConfirm>
        </div>
      </template>
    </BkResizeLayout>
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import screenfull from 'screenfull';
  import { format } from 'sql-formatter';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getProfileSql, upsertProfile } from '@services/source/profile';

  import { DBTypes } from '@common/const';

  import { messageError } from '@utils';

  import AutoFocusInput from './components/AutoFocusInput.vue';
  import CodeFormat from './components/CodeFormat.vue';
  import FontSetting from './components/FontSetting.vue';
  import FrequentQuery from './components/FrequentQuery.vue';
  import FullScreen from './components/FullScreen.vue';
  import MyCollection from './components/MyCollection.vue';

  export type SqlProfile = ServiceReturnType<typeof getProfileSql>;

  interface Props {
    dbType?: DBTypes;
  }

  type Emits = (e: 'change', value: string) => void;

  interface Exposes {
    updateCollectPanel: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.SQLSERVER,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  let editor: monaco.editor.IStandaloneCodeEditor;

  const { t } = useI18n();

  const rootRef = ref();
  const editorRef = ref();
  const isFullscreen = ref(false);
  const currentOperation = ref('query');
  const collectionRenderKey = ref(0);
  const collectName = ref('');
  const divideMin = ref(290);
  const sqlProfile = ref<SqlProfile>();

  const operationList = [
    {
      icon: 'dingwei',
      name: t('常用查询'),
      value: 'query',
    },
    {
      icon: 'wenjian',
      name: t('我的收藏'),
      value: 'collect',
    },
  ];

  const { run: fetchProfileSql } = useRequest(getProfileSql, {
    manual: true,
    onSuccess(data) {
      // 临时处理
      if (Array.isArray(data)) {
        sqlProfile.value = {};
      } else {
        sqlProfile.value = data;
      }
    },
  });

  watch(currentOperation, () => {
    if (currentOperation.value !== '') {
      divideMin.value = currentOperation.value === 'query' ? 290 : 450;
      return;
    }

    divideMin.value = 0;
  });

  watch(
    modelValue,
    () => {
      setTimeout(() => {
        if (modelValue.value !== editor?.getValue()) {
          editor?.setValue(modelValue.value);
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleChooseSql = (sql: string) => {
    modelValue.value = sql;
  };

  const handleClickCollect = async () => {
    if (!collectName.value) {
      messageError(t('收藏名称不能为空'));
      return;
    }

    if (!sqlProfile.value![props.dbType]) {
      sqlProfile.value![props.dbType] = [];
    }
    const nameList = sqlProfile.value![props.dbType].map((item) => item.name);
    if (nameList.includes(collectName.value)) {
      collectName.value = '';
      messageError(t('收藏名称已存在'));
      return;
    }

    sqlProfile.value![props.dbType].push({
      is_top: false,
      name: collectName.value,
      sql: modelValue.value,
    });
    await upsertProfile({
      label: 'SQL',
      values: sqlProfile.value,
    });
    collectName.value = '';
    fetchProfileSql();
  };

  const handleChangeOperation = (operation: string) => {
    if (currentOperation.value === operation) {
      currentOperation.value = '';
      return;
    }
    currentOperation.value = operation;
  };

  const handleToggleScreenfull = () => {
    if (screenfull.isFullscreen) {
      isFullscreen.value = true;
    } else {
      isFullscreen.value = false;
    }
    editor.layout();
  };

  const handleReize = () => {
    editor.layout();
  };

  const handleChangeFullScreen = () => {
    screenfull.toggle(rootRef.value);
  };

  const handleChangeFontSize = (fontSize: number) => {
    editor.updateOptions({ fontSize });
  };

  const handleCodeFormat = () => {
    modelValue.value = format(modelValue.value);
  };

  const handleAfterResize = () => {
    collectionRenderKey.value += 1;
  };

  fetchProfileSql();

  onMounted(() => {
    nextTick(() => {
      editor = monaco.editor.create(editorRef.value, {
        automaticLayout: true,
        fontSize: 16,
        language: 'sql',
        lineNumbersMinChars: 3,
        minimap: {
          enabled: false,
        },
        readOnly: false,
        renderLineHighlight: 'none',
        scrollbar: {
          alwaysConsumeMouseWheel: false,
        },
        theme: 'vs-dark',
        wordWrap: 'on',
      });
      editor.onDidChangeModelContent(() => {
        const value = editor.getValue();
        if (value !== modelValue.value) {
          modelValue.value = value;
          emits('change', value);
        }
      });
    });

    screenfull.on('change', handleToggleScreenfull);
    window.addEventListener('resize', handleReize);
  });

  onBeforeUnmount(() => {
    editor.dispose();
    screenfull.off('change', handleToggleScreenfull);
    window.removeEventListener('resize', handleReize);
  });

  defineExpose<Exposes>({
    updateCollectPanel() {
      handleAfterResize();
    },
  });
</script>
<style lang="less" scoped>
  .sql-execute-editor {
    position: relative;
    z-index: 0;
    height: 100%;

    &.is-full-screen {
      display: flex;
      height: 100vh;
      flex-direction: column;
    }

    :deep(.bk-resize-layout-aside-content) {
      height: calc(100% - 40px) !important;
    }

    .editor-layout-header {
      display: flex;
      align-items: center;
      height: 40px;
      padding-right: 16px;
      padding-left: 25px;
      font-size: 12px;
      color: #c4c6cc;
      background: #2e2e2e;

      .query-operation-main {
        display: flex;
        margin-left: auto;
        font-size: 12px;
        cursor: pointer;

        .operation-item {
          display: flex;
          width: 90px;
          align-items: center;
          justify-content: center;
          color: #c4c6cc;

          &.operation-item-active {
            color: #699df4;
          }
        }
      }

      .editro-action-box {
        display: flex;
        color: #979ba5;
        align-items: center;

        & > * {
          cursor: pointer;
        }
      }
    }

    .editor-main-resizer {
      :deep(.bk-resize-trigger) {
        background-color: #1a1a1a;
        height: calc(100% - 40px);

        &:hover {
          border-left: 1px solid #699df4;
        }
      }
    }
  }
</style>
<style lang="less">
  .editor-operate-main {
    display: flex;
    height: 56px;
    padding-left: 24px;
    background-color: #1a1a1a;
    align-items: center;

    .collect-btn {
      width: 64px;
      height: 28px;
      background: #313238;
      border: 1px solid #63656e;
      border-radius: 2px;
    }
  }

  .editor-collect-main {
    .collect-title {
      position: relative;

      &::after {
        position: absolute;
        top: 2px;
        left: 28px;
        color: #ea3636;
        content: '*';
      }
    }
  }
</style>
