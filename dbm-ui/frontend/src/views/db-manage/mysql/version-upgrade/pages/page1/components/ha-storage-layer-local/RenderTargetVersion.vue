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
  <BkLoading :loading="isLoading">
    <div
      v-overflow-tips
      class="capacity-box"
      :class="{ 'default-display': !data }">
      <span
        v-if="!data"
        style="color: #c4c6cc">
        {{ t('选择集群后自动生成') }}
      </span>
      <div
        v-else
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            <span>{{ data.currentVersion }}</span>
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('版本包文件') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="packageSelectRef"
              is-plain
              :list="packageSelectList"
              :model-value="localPackage"
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
            {{ charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            <span>{{ data.moduleName }}</span>
          </div>
        </div>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import { queryMysqlHigherVersionPkgList } from '@services/source/mysqlToolbox';

  import TableEditSelect, { type IListItem } from '@views/db-manage/mysql/common/edit/Select.vue';

  interface Props {
    isLoading: boolean;
    data?: {
      clusterId: number;
      clusterType: string;
      currentVersion: string;
      moduleName: string;
      moduleId: number;
    };
    targetVersion?: string;
    targetPackage?: number;
    targetModule?: number;
  }

  interface Emits {
    (e: 'module-change', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      pkg_id: number;
      display_info: {
        target_version: string;
        target_package: string;
      };
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    targetVersion: undefined,
    targetPackage: undefined,
    targetModule: undefined,
    isLocal: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const packageSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localVersion = ref<string>('');
  const localPackage = ref<number | ''>('');
  const localModule = ref<number | ''>('');
  const packageSelectList = ref<IListItem[]>([]);
  const charset = ref('');

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const packageRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('版本包文件不能为空'),
    },
  ];

  const { run: queryMysqlHigherVersionPkgListRun } = useRequest(queryMysqlHigherVersionPkgList, {
    manual: true,
    onSuccess(versions) {
      packageSelectList.value = versions.map((packageItem) => ({
        id: packageItem.pkg_id,
        name: packageItem.pkg_name,
      }));
      if (versions.length) {
        localPackage.value = versions[0].pkg_id;
      }
    },
  });

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      // const moduleList: IListItem[] = [];
      const { moduleId } = props.data!;
      const currentModule = modules.find((moduleItem) => moduleItem.db_module_id === moduleId);
      if (currentModule) {
        const currentCharset = currentModule.db_module_info.conf_items.find(
          (confItem) => confItem.conf_name === 'charset',
        )!.conf_value;
        charset.value = currentCharset;
        emits('module-change', currentCharset);

        // modules.forEach((moduleItem) => {
        //   let moduleItemCharset = '';
        //   let moduleItemDbVersion = '';
        //   moduleItem.db_module_info.conf_items.forEach((confItem) => {
        //     if (confItem.conf_name === 'charset') {
        //       moduleItemCharset = confItem.conf_value;
        //     } else if (confItem.conf_name === 'db_version') {
        //       moduleItemDbVersion = confItem.conf_value;
        //     }
        //   });
        //   if (moduleItemCharset === currentCharset && moduleItemDbVersion === localVersion.value) {
        //     moduleList.push({
        //       ...moduleItem,
        //       id: moduleItem.db_module_id,
        //       name: moduleItem.name,
        //     });
        //   }
        // });
        // moduleSelectList.value = moduleList;
      }
    },
  });

  watch(
    () => props.data?.clusterId,
    () => {
      if (props.data?.clusterId) {
        queryMysqlHigherVersionPkgListRun({
          cluster_id: props.data.clusterId,
          higher_major_version: false,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.targetVersion,
    () => {
      if (props.targetVersion) {
        localVersion.value = props.targetVersion;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.targetPackage,
    () => {
      if (props.targetPackage) {
        localPackage.value = props.targetPackage;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.targetModule,
    () => {
      if (props.targetModule) {
        localModule.value = props.targetModule;
      }
    },
    {
      immediate: true,
    },
  );

  const fetchModuleList = () => {
    if (props.data) {
      fetchModules({
        bk_biz_id: bizId,
        cluster_type: props.data.clusterType,
      });
    }
  };

  watch(
    () => props.data?.moduleName,
    () => {
      if (props.data?.moduleName) {
        fetchModuleList();
      }
    },
    {
      immediate: true,
    },
  );

  const handlePackageChange = (value: number) => {
    localPackage.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return packageSelectRef.value!.getValue().then(() => ({
        pkg_id: localPackage.value as number,
        display_info: {
          target_version: localVersion.value,
          target_package: packageSelectList.value.find((item) => item.id === localPackage.value)?.name || '',
        },
      }));
    },
  });
</script>

<style lang="less" scoped>
  .capacity-box {
    padding: 8px 16px;
    overflow: hidden;
    line-height: 26px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .display-content {
      display: flex;
      flex-direction: column;

      .content-item {
        display: flex;
        align-items: center;
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

  .module-select-item {
    display: flex;
    align-items: center;
    width: 100%;
    user-select: none;

    .not-permission {
      * {
        color: #70737a !important;
      }
    }
  }

  .module-select-footer {
    display: flex;
    height: 100%;
    color: #63656e;
    align-items: center;
    justify-content: center;

    .plus-button {
      flex: 1;
      padding-left: 36px;
    }

    .refresh-button {
      width: 42px;
      border-left: 1px solid #dcdee5;
    }

    .footer-icon {
      font-size: 16px;
    }
  }
</style>
