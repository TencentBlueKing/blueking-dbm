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
    field="target_version"
    :label="t('目标版本')"
    :min-width="200"
    required
    :rules="rules">
    <EditableBlock>
      <div
        v-if="cluster.id"
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            {{ currentModule?.db_module_name || '' }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            {{ currentModule?.db_version || '' }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ currentModule?.charset || '' }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="packageSelectRef"
              is-plain
              :list="packageSelectList"
              :model-value="pkgId"
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
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getVersionModules } from '@services/source/mysqlToolbox';

  import { ClusterTypes } from '@common/const';

  import TableEditSelect from '@views/db-manage/mysql/common/edit/Select.vue';

  type ModulesInfo = ServiceReturnType<typeof getVersionModules>[0];

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    } & TendbhaModel;
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

  const newDbModuleId = defineModel<number>('newDbModuleId', {
    required: true,
  });

  const pkgId = defineModel<number>('pkgId', {
    required: true,
  });

  const { t } = useI18n();

  const packageSelectList = ref<
    {
      id: number;
      name: string;
    }[]
  >([]);
  const moduleSelectList = ref<
    Array<
      {
        id: number;
        info: string;
        name: string;
      } & ModulesInfo
    >
  >([]);
  const currentModule = ref<ModulesInfo>();

  const packageRules = [
    {
      message: t('版本包文件不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];
  const rules = [
    {
      message: t('请确保选填完整'),
      trigger: 'blur',
      validator: () => _.every(modelValue.value, _.identity),
    },
  ];

  const { run: fetchModuleList } = useRequest(getVersionModules, {
    manual: true,
    onSuccess(data) {
      moduleSelectList.value = data.map((module) => ({
        ...module,
        id: module.db_module_id,
        info: `${module.db_version || ''}，${module.charset || ''}`,
        name: module.db_module_name,
      }));

      const [firstModule] = moduleSelectList.value;
      if (firstModule) {
        newDbModuleId.value = firstModule.id;
        currentModule.value = firstModule;

        packageSelectList.value = firstModule.pkg_list.map((item) => ({
          id: item.pkg_id,
          name: item.pkg_name,
        }));

        const [firstPackage] = packageSelectList.value;
        if (firstPackage) {
          pkgId.value = firstPackage.id;
        }

        modelValue.value = {
          charset: firstModule.charset,
          db_module_name: firstModule.db_module_name,
          db_version: firstModule.db_version,
          pkg_name: firstPackage?.name || '',
        };
      }
    },
  });

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        fetchModuleList({
          cluster_id: props.cluster.id,
          higher_major_version: false,
          higher_sub_version: true,
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 单据克隆回填
  watch(moduleSelectList, () => {
    if (modelValue.value.db_module_name) {
      pkgId.value = Number(_.get(_.find(packageSelectList.value, { name: modelValue.value.pkg_name }), 'id', 0));
      newDbModuleId.value = Number(
        _.get(_.find(moduleSelectList.value, { name: modelValue.value.db_module_name }), 'id', 0),
      );
    }
  });

  const handlePackageChange = (value: number) => {
    const findPackage = packageSelectList.value.find((item) => item.id === value);
    if (findPackage) {
      pkgId.value = value;
      modelValue.value.pkg_name = findPackage.name;
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
      }
    }
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
