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
  <EditableColumn
    field="cluster.current_version"
    :label="t('当前版本')"
    :min-width="200"
    required>
    <EditableBlock v-if="cluster.id">
      <div class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            {{ cluster.current_version }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            {{ cluster.package_version }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            {{ cluster.db_module_name }}
          </div>
        </div>
      </div>
    </EditableBlock>
    <EditableBlock
      v-else
      :placeholder="t('自动生成')" />
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';

  interface Props {
    cluster: {
      cluster_type: string;
      current_version: string;
      db_module_id: number;
      db_module_name: string;
      id: number;
      package_version: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const charset = ref('');

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const currentModule = modules.find((moduleItem) => moduleItem.db_module_id === props.cluster.db_module_id);
      if (currentModule) {
        const currentCharset = currentModule.db_module_info.conf_items.find(
          (confItem) => confItem.conf_name === 'charset',
        )!.conf_value;
        charset.value = currentCharset;
      }
    },
  });

  watch(
    () => props.cluster.cluster_type,
    (value) => {
      if (value) {
        fetchModules({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: value,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .display-content {
    display: flex;
    flex-direction: column;

    .content-item {
      display: flex;
      width: 100%;

      .item-title {
        width: 72px;
        text-align: right;
      }

      .item-content {
        flex: 1;
        display: flex;
        align-items: center;
        overflow: hidden;

        .percent {
          margin-left: 4px;
          font-size: 12px;
          font-weight: bold;
          color: #313238;
        }

        .spec {
          margin-left: 2px;
          font-size: 12px;
          color: #979ba5;
        }

        :deep(.render-spec-box) {
          height: 22px;
          padding: 0;
        }
      }
    }
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }
</style>
