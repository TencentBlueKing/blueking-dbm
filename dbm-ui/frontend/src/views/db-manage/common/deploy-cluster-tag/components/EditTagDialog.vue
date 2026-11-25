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
  <DbDialog
    class="deploy-cluster-tag-dialog"
    :is-show="isShow"
    :quick-close="false"
    render-directive="if"
    :width="660"
    @closed="handleClose">
    <template #header>
      <div class="header-main">
        <div class="main-title">{{ t('编辑标签') }}</div>
        <template v-if="domain">
          <div class="split-line"></div>
          <div class="sub-title">{{ domain }}</div>
        </template>
      </div>
    </template>
    <TagOperation
      ref="tagOperationRef"
      :biz-id="bizId"
      :data="tagPairData" />
    <template #footer>
      <div class="footer-wrapper">
        <BkButton
          class="mr-8"
          :loading="confirmLoading"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </DbDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TagOperation from '@views/db-manage/common/cluster-batch-add-tag/components/tag-operation/Index.vue';

  import { messageError } from '@utils';

  interface Props {
    /** 标签候选查询的业务 ID，不传回退到当前页面业务 */
    bizId?: number | '';
    /** 弹窗标题右侧的集群标识 */
    domain?: string;
    isShow: boolean;
    /** 当前行的标签数据，单键对象数组 */
    tags?: Record<string, string>[];
  }

  type Emits = {
    (e: 'close'): void;
    (e: 'confirm', value: Record<string, string>[]): void;
  };

  const props = withDefaults(defineProps<Props>(), {
    bizId: window.PROJECT_CONFIG.BIZ_ID,
    domain: '',
    tags: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tagOperationRef = ref<InstanceType<typeof TagOperation>>();
  const confirmLoading = ref(false);

  // 单键对象数组转编辑器的 key/value 行数据
  const tagPairData = computed(() =>
    props.tags.map((item, index) => ({
      id: index,
      key: Object.keys(item)[0] ?? '',
      value: Object.values(item)[0] ?? '',
    })),
  );

  const handleClose = () => {
    emits('close');
  };

  const handleConfirm = async () => {
    try {
      confirmLoading.value = true;
      const tagInfo = await tagOperationRef.value?.getValue();
      if (!tagInfo?.length) {
        messageError(t('请完善标签键值'));
        return;
      }
      // 转回单键对象数组写回当前行
      emits(
        'confirm',
        tagInfo.map(({ key, value }) => ({ [key]: value })),
      );
    } finally {
      confirmLoading.value = false;
    }
  };
</script>

<style lang="less">
  .deploy-cluster-tag-dialog {
    .bk-modal-wrapper {
      max-height: 80vh;

      .header-main {
        display: flex;
        align-items: center;

        .main-title {
          font-size: 20px;
          color: #313238;
        }

        .split-line {
          width: 1px;
          height: 16px;
          margin-right: 8px;
          margin-left: 10px;
          background-color: #979ba5;
        }

        .sub-title {
          font-size: 14px;
          color: #979ba5;
        }
      }

      .bk-modal-body {
        .bk-modal-content {
          max-height: calc(80vh - 100px) !important;
          overflow-y: auto;
        }
      }

      .footer-wrapper {
        button {
          width: 64px;
        }
      }
    }
  }
</style>
