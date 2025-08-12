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
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-if="cluster.id"
        class="display-content">
        <div class="content-item">
          <div class="item-title">{{ t('数据库版本') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="versionSelectRef"
              is-plain
              :list="versionSelectList"
              :model-value="dbVersion"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="versionRules"
              @change="(value) => handleVersionChange(value as string)">
            </TableEditSelect>
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
        <div class="content-item">
          <div class="item-title">{{ t('字符集') }}：</div>
          <div class="item-content">
            {{ charset }}
          </div>
        </div>
        <div class="content-item">
          <div class="item-title">{{ t('绑定模块') }}：</div>
          <div class="item-content">
            <TableEditSelect
              ref="moduleSelectRef"
              is-plain
              :list="moduleSelectList"
              :model-value="newDbModuleId"
              :placeholder="t('请选择')"
              :pop-width="240"
              :rules="moduleRules"
              @change="(value) => handleModuleChange(value as number)">
              <template #default="{ item }">
                <AuthTemplate
                  action-id="dbconfig_view"
                  :biz-id="item.bk_biz_id"
                  :permission="item.permission.dbconfig_view"
                  resource="tendbcluster"
                  style="flex: 1">
                  <template #default="{ permission }">
                    <div class="module-option-item">
                      <div
                        class="module-option-label"
                        :class="{ 'not-permission': !permission }"
                        data-id="dbconfig_view">
                        {{ item.alias_name }}
                      </div>
                      <div class="module-opiton-info">
                        {{ item.info }}
                      </div>
                    </div>
                  </template>
                </AuthTemplate>
              </template>
              <template #footer>
                <div class="module-select-footer">
                  <AuthButton
                    action-id="dbconfig_edit"
                    :biz-id="bizId"
                    class="plus-button"
                    resource="tendbcluster"
                    text
                    @click="handleCreateModule">
                    <DbIcon
                      class="footer-icon mr-4"
                      type="plus-8" />
                    {{ t('跳转新建模块') }}
                  </AuthButton>
                  <BkButton
                    class="refresh-button"
                    text
                    @click="handleRefreshModule">
                    <DbIcon
                      class="footer-icon"
                      type="refresh-2" />
                  </BkButton>
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

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getModules } from '@services/source/cmdb';
  import { querySpiderHigherVersionPkgList } from '@services/source/mysqlToolbox';

  import { TicketTypes } from '@common/const';

  import TableEditSelect, { type IListItem } from '@views/db-manage/mysql/common/edit/Select.vue';

  interface Props {
    cluster: TendbClusterModel;
    /**
     * 高于当前集群主版本, 默认false
     */
    higherMajorVersion?: boolean;
    /**
     * 高于当前集群子版本, 默认false
     */
    higherSubVersion?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    higherMajorVersion: false,
    higherSubVersion: false,
  });

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

  const route = useRoute();
  const router = useRouter();

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const versionSelectList = ref<IListItem[]>([]);
  const packageSelectList = ref<IListItem[]>([]);
  const moduleSelectList = ref<IListItem[]>([]);
  const charset = ref('');
  const dbVersion = ref('');

  const versionRules = [
    {
      message: t('数据库版本不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];
  const packageRules = [
    {
      message: t('版本包文件不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];
  const moduleRules = [
    {
      message: t('绑定模块不能为空'),
      validator: (value: string) => Boolean(value),
    },
  ];
  const rules = [
    {
      message: t('请确保选填完整'),
      trigger: 'blur',
      validator: () => {
        return new Promise((resolve) => {
          // 整理提单参数一并抛出
          modelValue.value = {
            charset: charset.value,
            db_module_name: _.get(_.find(moduleSelectList.value, { id: newDbModuleId.value }), 'name', ''),
            db_version: dbVersion.value,
            pkg_name: _.get(_.find(packageSelectList.value, { id: pkgId.value }), 'name', ''),
          };
          resolve(modelValue.value);
        }).then(() => {
          return _.every(modelValue.value, _.identity);
        });
      },
    },
  ];

  function fetchModuleList() {
    if (props.cluster.cluster_type) {
      fetchModules({
        bk_biz_id: bizId,
        cluster_type: props.cluster.cluster_type,
      });
    }
  }

  const { run: querySpiderHigherVersionPkgListRun } = useRequest(querySpiderHigherVersionPkgList, {
    manual: true,
    onSuccess(versions) {
      versionSelectList.value = _.uniqBy(
        versions.map((item) => ({
          id: item.version,
          name: item.version,
        })),
        'id',
      );
      packageSelectList.value = versions.map((packageItem) => ({
        id: packageItem.pkg_id,
        name: packageItem.pkg_name,
      }));
      if (versions.length) {
        const [lastestVersion] = versions;
        dbVersion.value = lastestVersion.version;
        pkgId.value = lastestVersion.pkg_id;
        fetchModuleList();
      }
    },
  });

  const { run: fetchModules } = useRequest(getModules, {
    manual: true,
    onSuccess(modules) {
      const currentModule = modules.find((m) => m.db_module_id === props.cluster.db_module_id);
      if (!currentModule) return;

      const confItems = _.keyBy(currentModule.db_module_info.conf_items, 'conf_name');
      charset.value = confItems.charset?.conf_value || '';
      const backendVersion = confItems.spider_version?.conf_value || '';
      const backendDbVersion = confItems.db_version?.conf_value || '';

      const filtered = [];
      for (const module of modules) {
        const conf = Object.fromEntries(
          module.db_module_info.conf_items.map(({ conf_name, conf_value }) => [conf_name, conf_value]),
        );
        const isBackendModules = props.higherSubVersion
          ? conf.spider_version === dbVersion.value
          : conf.spider_version === backendVersion && conf.db_version === backendDbVersion;
        if (conf.charset === charset.value && isBackendModules) {
          filtered.push({
            alias_name: module.alias_name,
            bk_biz_id: module.bk_biz_id,
            disabled: false,
            id: module.db_module_id,
            info: `${conf.spider_version || ''}，${conf.charset || ''}`,
            name: module.name,
            permission: module.permission,
          });
        }
      }
      moduleSelectList.value = filtered;
      const [first] = filtered;
      if (first) {
        newDbModuleId.value = first.id;
      }
    },
  });

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        querySpiderHigherVersionPkgListRun({
          cluster_id: props.cluster.id,
          higher_major_version: props.higherMajorVersion,
          higher_sub_version: props.higherSubVersion,
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
      dbVersion.value = modelValue.value.db_version;
      pkgId.value = Number(_.get(_.find(packageSelectList.value, { name: modelValue.value.pkg_name }), 'id', 0));
      charset.value = modelValue.value.charset;
      newDbModuleId.value = Number(
        _.get(_.find(moduleSelectList.value, { name: modelValue.value.db_module_name }), 'id', 0),
      );
    }
  });

  const handleVersionChange = (value: string) => {
    dbVersion.value = value;
    fetchModuleList();
  };

  const handlePackageChange = (value: number) => {
    const findVersion = packageSelectList.value.find((item) => item.id === value);
    if (findVersion) {
      pkgId.value = value;
    }
  };

  const handleModuleChange = (value: number) => {
    newDbModuleId.value = value;
  };

  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'SelfServiceCreateDbModule',
      params: {
        bk_biz_id: bizId,
        type: TicketTypes.TENDBCLUSTER_APPLY,
      },
      query: {
        from: route.name as string,
      },
    });
    window.open(url.href, '_blank');
  };

  const handleRefreshModule = () => {
    fetchModuleList();
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

  .module-option-item {
    display: flex;
    width: 100%;

    .module-option-label {
      flex: 1;
      width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .module-opiton-info {
      margin-left: auto;
      color: #979ba5;
    }

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
