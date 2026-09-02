<template>
  <div class="mongo-host-selector-preview">
    <div class="preview-header">
      <span>{{ t('结果预览') }}</span>
      <BkDropdown
        class="preview-dropdown"
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click">
        <i class="db-icon-more preview-trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem
              :disabled="list.length === 0"
              @click="handleClear">
              {{ t('清空所有') }}
            </BkDropdownItem>
            <BkDropdownItem
              :disabled="list.length === 0"
              @click="handleCopy">
              {{ t('复制所有IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
    <BkException
      v-if="list.length === 0"
      class="mt-50"
      :description="t('暂无数据_请从左侧添加对象')"
      scene="part"
      type="empty" />
    <div
      v-else
      class="preview-list db-scroll-y">
      <div
        v-for="(item, index) in list"
        :key="item.ip"
        v-test="{ type: 'span', value: 'instanceSelectorPreviewItem' }"
        class="preview-item">
        <span
          v-overflow-tips
          class="text-overflow">
          {{ item.ip }}
        </span>
        <DbIcon
          type="close preview-item-remove"
          @click="handleRemove(index)" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  import { type MongoHostRow } from '../../types';

  interface Props {
    list: MongoHostRow[];
  }

  type Emits = (e: 'change', value: MongoHostRow[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleRemove = (index: number) => {
    const nextList = [...props.list];
    nextList.splice(index, 1);
    emits('change', nextList);
  };

  const handleClear = () => {
    emits('change', []);
  };

  const handleCopy = () => {
    execCopy(props.list.map((item) => item.ip).join('\n'), t('复制成功'));
  };
</script>
<style lang="less">
  .mongo-host-selector-preview {
    display: flex;
    height: 100%;
    max-height: 625px;
    padding: 12px 24px;
    overflow: hidden;
    font-size: @font-size-mini;
    background-color: #f5f6fa;
    flex-direction: column;

    .preview-header {
      display: flex;
      padding-bottom: 16px;
      align-items: center;

      > span {
        flex: 1;
        font-size: @font-size-normal;
        color: @title-color;
      }

      .preview-dropdown {
        font-size: 0;
        line-height: 20px;
      }

      .preview-trigger {
        display: block;
        font-size: 18px;
        color: @gray-color;
        cursor: pointer;

        &:hover {
          background-color: @bg-disable;
          border-radius: 2px;
        }
      }
    }

    .preview-list {
      display: flex;
      flex: 1;
      overflow-y: auto;
      flex-direction: column;

      .preview-item {
        display: flex;
        padding: 0 12px;
        margin-bottom: 2px;
        line-height: 32px;
        background-color: @bg-white;
        border-radius: 2px;
        justify-content: space-between;
        align-items: center;

        .preview-item-remove {
          display: none;
          font-size: @font-size-large;
          font-weight: bold;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            color: @default-color;
          }
        }

        &:hover {
          .preview-item-remove {
            display: block;
          }
        }
      }
    }
  }
</style>
