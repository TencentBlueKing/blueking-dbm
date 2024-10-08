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
  <BkDialog
    class="review-data-dialog"
    :is-show="isShow"
    :title="title"
    @closed="handleClose">
    <div class="review-data-wrapper">
      <div class="tip">{{ tip }}</div>
      <div class="selected-wrapper">
        <div class="selected-title">
          <I18nT keypath="已选择以下n台主机">
            <span class="selected-count">
              {{ selected.length }}
            </span>
          </I18nT>
        </div>
        <div class="selected-content">
          <div
            v-for="item in selected"
            :key="item"
            class="selected-item">
            {{ item }}
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <div class="footer">
        <BkButton
          :loading="loading"
          style="width: 88px"
          :theme="theme"
          @click="handleConfirm"
          >{{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-9 operation-btn"
          :loading="loading"
          style="width: 88px"
          @click="handleClose"
          >{{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  interface Props {
    title: string;
    tip: string;
    loading: boolean;
    selected: string[];
    theme?: 'primary' | 'danger';
  }

  interface Emits {
    (e: 'confirm'): void;
    (e: 'cancel'): void;
  }

  withDefaults(defineProps<Props>(), {
    theme: 'primary',
  });

  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const handleConfirm = () => {
    emits('confirm');
    isShow.value = false;
  };

  const handleClose = () => {
    emits('cancel');
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .review-data-wrapper {
    font-size: 14px;

    .tip {
      background: #f5f6fa;
      border-radius: 2px;
      padding: 12px 16px;
      margin-bottom: 8px;
    }

    .selected-wrapper {
      border: 1px solid #eaebf0;
      border-radius: 2px;
      max-height: 192px;
      overflow-y: auto;

      .selected-title {
        width: 100%;
        padding: 5px 16px;
        background: #f0f1f5;
        color: #313238;
        position: sticky;
        top: 0;

        .selected-count {
          font-weight: 700;
        }
      }

      .selected-content {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        font-size: 12px;

        .selected-item {
          padding: 6px 16px;

          &:nth-child(4n-3),
          &:nth-child(4n-2) {
            background-color: #ffffff;
          }

          &:nth-child(4n-1),
          &:nth-child(4n) {
            background-color: #fafbfd;
          }
        }
      }
    }
  }

  .footer {
    display: flex;
    justify-content: center;
  }
</style>

<style lang="less">
  .review-data-dialog {
    .bk-dialog-footer {
      background-color: #fff !important;
      border: none !important;
      padding-top: 0 !important;
      padding-bottom: 24px !important;
    }
  }
</style>
