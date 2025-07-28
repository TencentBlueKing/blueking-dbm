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
  <BkButton
    class="checksum-batch"
    @click="() => (isShow = true)">
    <i class="bk-dbm-icon db-icon-add" />
    {{ t('批量录入') }}
  </BkButton>
  <BkDialog
    :is-show="isShow"
    :quick-close="false"
    :title="t('xx_批量录入', { title: route.meta.tabName || route.meta.navName })"
    :width="1200"
    @closed="handleClose">
    <div class="batch-input">
      <div class="batch-input-format">
        <div
          v-for="(item, index) in props.config"
          :key="index"
          class="batch-input-format-item">
          <strong>
            {{ item.label }}
          </strong>
          <p class="pt-8">{{ item.case }}</p>
        </div>
        <DbIcon
          v-bk-tooltips="t('复制格式')"
          class="batch-input-copy"
          type="copy"
          @click="handleCopy" />
      </div>
      <BkInput
        v-model="inputValue"
        class="batch-input-textarea"
        :placeholder="
          t(
            '1. 多个字段以空白符（空格、制表符）分割_2. 列留空，请输入 NULL_3. 日期时间使用T分割。如：2025-03-11T10:26:13_4. 单元格内换行，用\\n 分割。如：我是第一行\\n我是第二行_5. 枚举类型，请输入选项值',
          )
        "
        type="textarea" />
      <BkCheckbox v-model="isClear">{{ t('覆盖表格已有数据') }}</BkCheckbox>
    </div>
    <template #footer>
      <BkButton
        class="mr-8 w-88"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  interface Props {
    /**
     * @description 批量输入配置
     * @example [{ key: 'db_name', label: 'DB 名称', case: 'db1 db2 db3' }]
     * @default []
     */
    config: {
      case: string;
      key: string;
      label: string;
    }[];
  }

  type Emits = (e: 'change', data: Record<string, any>[], isClear: boolean) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();
  const route = useRoute();

  const isShow = ref(false);
  const inputValue = ref('');
  const isClear = ref(false);

  const handleCopy = () => {
    copy(props.config.map((item) => `${item.case}`).join('\t'));
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = () => {
    if (inputValue.value === '') {
      handleClose();
      return;
    }

    const lines = inputValue.value.split(/\n|\\n/).filter((text) => text);

    const getContents = (value: string) => {
      const contents = value
        .trim() // 清除前后空格
        .replace(/\s+/g, ' ') // 替换多余空格
        .split(' '); // 通过空格分割
      return contents;
    };

    const result = lines.map((item) => {
      const contents = getContents(item);
      return props.config.reduce<Record<string, any>>((acc, cur, index) => {
        const value = contents[index];
        Object.assign(acc, {
          [cur.key]: value === 'NULL' ? '' : value,
        });
        return acc;
      }, {});
    });

    emits('change', result, isClear.value);
    handleClose();
  };
</script>

<style lang="less" scoped>
  .checksum-batch {
    .db-icon-add {
      margin-right: 4px;
      color: @gray-color;
    }
  }

  .batch-input {
    position: relative;

    .batch-input-format {
      display: flex;
      padding: 16px;
      background-color: #f5f7fa;
      border-radius: 2px;

      .batch-input-format-item {
        margin-right: 24px;
        font-size: @font-size-mini;
      }
    }

    .batch-input-copy {
      position: relative;
      top: 26px;
      width: 16px;
      height: 16px;
      color: @primary-color;
      cursor: pointer;
    }

    .batch-input-textarea {
      height: 310px;
      margin: 16px 0;

      :deep(textarea) {
        &::selection {
          background-color: #fdd;
        }
      }
    }
  }
</style>
