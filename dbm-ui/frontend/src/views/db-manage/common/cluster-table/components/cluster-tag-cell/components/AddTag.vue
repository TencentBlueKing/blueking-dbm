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
    class="cluster-add-tag-dialog-main"
    :is-show="isShow"
    :quick-close="false"
    render-directive="if"
    :width="660"
    @closed="handleClose"
    @confirm="handleConfirm">
    <template #header>
      <div class="header-main">
        <div class="main-title">{{ data.length ? t('编辑标签') : t('添加标签') }}</div>
        <div class="split-line"></div>
        <div class="sub-title">{{ domain }}</div>
      </div>
    </template>
    <TagOperation
      ref="tagOperationRef"
      :data="data" />
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
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { addClusterTagKeys, updateClusterTag } from '@services/source/dbbase';

  import TagOperation from '@views/db-manage/common/cluster-batch-add-tag/components/tag-operation/Index.vue';

  import type { ClusterModel, ISupportClusterType } from '../../../types';

  interface Props {
    clusterId: number;
    data: ClusterModel<ISupportClusterType>['tags'];
    domain: string;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const tagOperationRef = ref<InstanceType<typeof TagOperation>>();
  const confirmLoading = ref(false);

  const { run: handleAddClusterTagKeys } = useRequest(addClusterTagKeys, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      emits('success');
    },
  });

  const { run: handleUpdateClusterTag } = useRequest(updateClusterTag, {
    manual: true,
    onSuccess() {
      isShow.value = false;
      emits('success');
    },
  });

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = async () => {
    try {
      confirmLoading.value = true;
      const tagsInfo = await tagOperationRef.value!.getValue();
      if (tagsInfo) {
        if (!props.data.length) {
          // 新增
          handleAddClusterTagKeys({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_ids: [props.clusterId],
            tags: Object.values(tagsInfo).map((item) => item.value) as number[],
          });
        } else {
          // 更新
          handleUpdateClusterTag({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_id: props.clusterId,
            tags: Object.values(tagsInfo).map((item) => item.value) as number[],
          });
        }
      }
    } finally {
      confirmLoading.value = false;
    }
  };
</script>

<style lang="less">
  .cluster-add-tag-dialog-main {
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
