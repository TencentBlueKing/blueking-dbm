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
    field="cluster.master_domain"
    :label="t('目标版本')"
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
            <TableEditSelect
              ref="packageSelectRef"
              is-plain
              :list="packageSelectList"
              :model-value="modelValue.pkg_id"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="packageRules"
              @change="(value) => handlePackageChange(value as number)">
              <template #default="{ item, index }">
                <div class="target-version-select-option">
                  <div
                    v-overflow-tips
                    class="option-name">
                    {{ item.name }}
                  </div>
                  <BkTag
                    v-if="index === 0"
                    class="ml-4"
                    size="small"
                    theme="info">
                    {{ t('推荐') }}
                  </BkTag>
                </div>
              </template>
            </TableEditSelect>
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ modelValue.charset }}
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
  import { queryMysqlHigherVersionPkgList } from '@services/source/mysqlToolbox';

  import TableEditSelect, { type IListItem } from '@views/db-manage/mysql/common/edit/Select.vue';

  import { compareVersions } from '@utils';

  interface Props {
    cluster: {
      bk_cloud_id: number;
      cluster_type: string;
      current_version: string;
      db_module_id: number;
      db_module_name: string;
      id: number;
      master_domain: string;
      package_version: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    charset: string;
    pkg_id: number;
    target_package: string;
    target_version: string;
  }>({
    default: () => ({
      charset: '',
      pkg_id: 0,
      target_package: '',
      target_version: '',
    }),
  });

  const { t } = useI18n();

  const packageSelectList = ref<({ version: string } & IListItem)[]>([]);
  const packageRules = [
    {
      message: t('版本包文件不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];

  const { run: queryMysqlHigherVersionPkgListRun } = useRequest(queryMysqlHigherVersionPkgList, {
    manual: true,
    onSuccess(versions) {
      packageSelectList.value = versions
        .map((packageItem) => ({
          id: packageItem.pkg_id,
          name: packageItem.pkg_name,
          version: packageItem.version,
        }))
        .sort((a, b) => {
          return compareVersions(b.name, a.name);
        });
      if (versions.length) {
        const [lastestVersion] = versions;
        modelValue.value = {
          charset: '',
          pkg_id: lastestVersion.pkg_id,
          target_package: lastestVersion.pkg_name,
          target_version: lastestVersion.version,
        };
      }
    },
  });

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const currentModule = modules.find((moduleItem) => moduleItem.db_module_id === props.cluster.db_module_id);
      if (currentModule) {
        const currentCharset = currentModule.db_module_info.conf_items.find(
          (confItem) => confItem.conf_name === 'charset',
        )!.conf_value;
        modelValue.value.charset = currentCharset;
      }
    },
  });

  watch(
    () => props.cluster,
    () => {
      if (props.cluster.id) {
        queryMysqlHigherVersionPkgListRun({
          cluster_id: props.cluster.id,
          higher_major_version: false,
        });
      }
      if (props.cluster.cluster_type) {
        fetchModules({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: props.cluster.cluster_type,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handlePackageChange = (value: number) => {
    const findVersion = packageSelectList.value.find((item) => item.id === value);
    if (findVersion) {
      modelValue.value = {
        ...modelValue.value,
        pkg_id: findVersion.id as number,
        target_package: findVersion.name,
        target_version: findVersion.version,
      };
    }
  };
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
<style lang="less">
  .target-version-select-option {
    display: flex;
    align-items: center;

    .option-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
