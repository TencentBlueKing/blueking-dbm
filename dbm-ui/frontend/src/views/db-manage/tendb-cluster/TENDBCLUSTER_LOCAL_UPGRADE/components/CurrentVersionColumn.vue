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
    field="current_version"
    :label="t('当前版本')"
    :loading="loading"
    :min-width="200"
    required>
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-if="cluster.id"
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            {{ modelValue.db_module_name }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            {{ modelValue.db_version }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ modelValue.charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            {{ modelValue.pkg_name }}
          </div>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getModules } from '@services/source/cmdb';

  interface Props {
    cluster: TendbClusterModel;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    charset: string;
    db_module_name: string;
    db_version: string;
    pkg_name: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const { loading, run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const currentModule = modules.find((moduleItem) => moduleItem.db_module_id === props.cluster.db_module_id);
      if (currentModule) {
        const confItems = _.keyBy(currentModule.db_module_info.conf_items, 'conf_name');
        modelValue.value = {
          charset: confItems.charset?.conf_value || '',
          db_module_name: props.cluster.db_module_name,
          db_version: confItems.spider_version?.conf_value || '',
          pkg_name: _.uniq(props.cluster.spider_master.map((item) => item.version)).join(' | '),
        };
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
      }
    }
  }
</style>
