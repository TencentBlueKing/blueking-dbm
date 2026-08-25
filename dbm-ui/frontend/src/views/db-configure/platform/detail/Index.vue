<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <ApplyPermissionCatch>
    <div class="platform-detail-page">
      <div class="platform-detail-content">
        <!-- 参数信息 -->
        <div class="platform-info-card">
          <div class="param-operations mb-16">
            <AuthButton
              action-id="global_dbconfig_edit"
              :permission="permissions.global_dbconfig_edit"
              :resource="dbType"
              theme="primary"
              @click="handleAddParam">
              {{ t('新增参数') }}
            </AuthButton>
            <DbQuickSearch
              v-model="searchValue"
              :data="quickSearchData"
              parse-url
              :placeholder="t('搜索参数名_显示名_平台默认值_允许值_数据类型_重启生效_业务默认可见_业务可编辑')"
              style="width: 500px; margin-left: auto"
              @change="handleQuickSearchChange" />
          </div>
          <BkLoading :loading="paramLoading">
            <DbTable
              ref="paramTableRef"
              :data-source="paramDataSource"
              :default-limit="100"
              :filter-value="searchValue"
              row-key="conf_name"
              @clear-search="handleQuickSearchChange"
              @filter-change="handleFilterChange"
              @request-success="initDescriptionTippy">
              <TableColumn
                col-key="conf_name"
                ellipsis
                fixed="left"
                :min-width="250"
                :title="t('参数名')"
                :width="300">
                <template #default="{ row }">
                  {{ row.conf_name }}
                  <DbIcon
                    v-if="row.description"
                    class="param-desc-icon ml-4"
                    :data-conf-name="row.conf_name"
                    :data-description="row.description"
                    type="bk-dbm-icon db-icon-attention" />
                  <BkTag
                    v-if="getCreateFrom(row) !== ''"
                    class="ml-4"
                    theme="warning">
                    {{ t('平台自定义') }}
                  </BkTag>
                </template>
              </TableColumn>
              <TableColumn
                v-if="!isStandardDbConfig"
                col-key="conf_name_lc"
                ellipsis
                :title="t('显示名')"
                :width="120">
                <template #default="{ row }">
                  {{ row.conf_name_lc || '--' }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="value_default"
                ellipsis
                :title="t('平台默认值')"
                :width="180">
                <template #default="{ row }">
                  <span
                    v-if="row.value_default === ''"
                    class="no-constraint-text">
                    {{ t('空字符串') }}
                  </span>
                  <span v-else>
                    {{ row.flag_encrypt === 1 ? '******' : row.value_default }}
                  </span>
                </template>
              </TableColumn>
              <TableColumn
                col-key="value_allowed"
                ellipsis
                :title="t('允许值')"
                :width="220">
                <template #default="{ row }">
                  <template v-if="row.value_type_sub && row.value_type_sub !== 'STRING'">
                    <BkTag>{{ row.value_type_sub }}</BkTag>
                    <span class="ml-4">{{ row.value_allowed || '--' }}</span>
                  </template>
                  <span
                    v-else
                    class="no-constraint-text">
                    {{ NO_CONSTRAINT }}
                  </span>
                </template>
              </TableColumn>
              <TableColumn
                col-key="value_type"
                :filter="valueTypeFilter"
                :title="t('数据类型')"
                :width="100">
                <template #default="{ row }">
                  <BkTag v-if="row.value_type">
                    {{ row.value_type }}
                  </BkTag>
                  <span v-else>--</span>
                </template>
              </TableColumn>
              <TableColumn
                col-key="flag_visible"
                :filter="boolFilter"
                :width="120">
                <template #title>
                  <span
                    v-bk-tooltips="t('是否在业务配置页默认带出该参数；关闭后业务仍可通过「添加参数」主动加入')"
                    class="column-title-tips">
                    {{ t('业务默认可见') }}
                  </span>
                </template>
                <template #default="{ row }">
                  {{ row.flag_visible === 1 ? t('是') : t('否') }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="flag_readonly"
                :filter="boolFilter"
                :width="120">
                <template #title>
                  <span
                    v-bk-tooltips="t('控制业务侧是否可编辑该参数数值')"
                    class="column-title-tips">
                    {{ t('业务可编辑') }}
                  </span>
                </template>
                <template #default="{ row }">
                  {{ row.flag_readonly === 0 ? t('是') : t('否') }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="need_restart"
                :filter="boolFilter"
                :width="100">
                <template #title>
                  <span
                    v-bk-tooltips="t('预留配置下发场景；后续下发的存量实例后，是否需要重启实例生效')"
                    class="column-title-tips">
                    {{ t('重启生效') }}
                  </span>
                </template>
                <template #default="{ row }">
                  {{ row.need_restart === 1 ? t('是') : t('否') }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="row-operation"
                fixed="right"
                :title="t('操作')"
                :width="160">
                <template #default="{ row }">
                  <AuthTemplate
                    action-id="global_dbconfig_edit"
                    :permission="permissions.global_dbconfig_edit"
                    :resource="dbType">
                    <BkButton
                      class="mr-16"
                      text
                      theme="primary"
                      @click="handleEditParam(row)">
                      {{ t('编辑') }}
                    </BkButton>
                    <!-- 系统定义但平台修改：恢复初始值 -->
                    <BkButton
                      v-if="getCreateFrom(row) === 'def'"
                      class="mr-16"
                      text
                      theme="primary"
                      @click="handleRestoreParam(row)">
                      {{ t('恢复初始值') }}
                    </BkButton>
                    <!-- 平台自定义：删除（提交后端校验引用） -->
                    <BkButton
                      v-else-if="getCreateFrom(row) === 'plat'"
                      class="mr-16"
                      text
                      theme="primary"
                      @click="handleDeleteParam(row)">
                      {{ t('删除') }}
                    </BkButton>
                    <!-- 系统定义且未修改：删除置灰 -->
                    <BkButton
                      v-else
                      v-bk-tooltips="t('系统内置参数不允许删除')"
                      disabled
                      text>
                      {{ t('删除') }}
                    </BkButton>
                  </AuthTemplate>
                </template>
              </TableColumn>
            </DbTable>
          </BkLoading>
        </div>
      </div>
    </div>

    <!-- 新增/编辑参数侧滑 -->
    <ParamFormSideslider
      v-if="currentConfItem"
      ref="paramFormSliderRef"
      :conf-name-type-map="confNameTypeMap"
      :conf-type="confType"
      :namespace="currentConfItem!.namespace"
      :version="version"
      @success="fetchDetailData" />
  </ApplyPermissionCatch>
  <Teleport to="#dbContentTitleAppend">
    <div class="config-detail-header">
      <span class="config-detail-nav-title">
        {{ currentConfItem?.name }}
      </span>
      <BkTag theme="info">
        {{ clusterTypeInfos[clusterType]?.name || clusterType }}
      </BkTag>
      <span class="config-detail-meta">
        <span>{{ t('配置名称') }}：{{ detailData?.name || '--' }}</span>
        <span>
          {{ t('最近更新') }}：{{ detailData?.updated_by || '--' }} /
          {{ detailData?.updated_at ? utcDisplayTime(detailData.updated_at) : '--' }}
        </span>
        <span>{{ t('描述') }}：{{ detailData?.description || '--' }}</span>
      </span>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import type { Instance } from 'tippy.js';
  import { h } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    changeConfNames,
    getConfigBaseDetails,
    getConfigNames,
    getListConfNameTypes,
    getListConfTypes,
    type ParameterConfigItem,
  } from '@services/source/configs';

  import { clusterTypeInfos, type ClusterTypes, DBTypes } from '@common/const';
  import { dbTippy } from '@common/tippy';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import DbQuickSearch from '@components/db-quick-search/Index.vue';
  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { messageSuccess, utcDisplayTime } from '@utils';

  import ParamFormSideslider from './components/ParamFormSideslider.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const { clusterType, confType, version } = route.params as {
    clusterType: ClusterTypes;
    confType: string;
    version: string;
  };
  const dbType = clusterTypeInfos[clusterType as ClusterTypes]?.dbType || DBTypes.MYSQL;

  // 无约束标识常量（表格展示用）
  const NO_CONSTRAINT = t('无约束');

  const paramTableRef = ref<InstanceType<typeof DbTable>>();
  const paramFormSliderRef = ref<InstanceType<typeof ParamFormSideslider>>();

  const currentConfItem = ref<ServiceReturnType<typeof getListConfTypes>[number]>();
  type DetailResult = ServiceReturnType<typeof getConfigBaseDetails>;
  const detailData = ref<Partial<DetailResult>>({});
  const allConfItems = ref<DetailResult['conf_items']>([]);

  const paramLoading = ref(false);

  // 快速搜索
  const searchValue = ref<Record<string, any>>({});
  const baseQuickSearchData = [
    { id: 'conf_name', name: t('参数名'), type: 'input' as const },
    { id: 'conf_name_lc', name: t('显示名'), type: 'input' as const },
    { id: 'value_default', name: t('平台默认值'), type: 'input' as const },
    { id: 'value_allowed', name: t('允许值'), type: 'input' as const },
    {
      id: 'value_type',
      name: t('数据类型'),
      type: 'multiple' as const,
    },
    {
      id: 'flag_visible',
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
      name: t('业务默认可见'),
      type: 'multiple' as const,
    },
    {
      id: 'flag_readonly',
      list: [
        { label: t('是'), value: '0' },
        { label: t('否'), value: '1' },
      ],
      name: t('业务可编辑'),
      type: 'multiple' as const,
    },
    {
      id: 'need_restart',
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
      name: t('重启生效'),
      type: 'multiple' as const,
    },
  ];

  /** 动态补充 value_type 的选项列表 */
  const quickSearchData = computed(() =>
    baseQuickSearchData.map((item) => {
      if (item.id !== 'value_type') return item;
      return {
        ...item,
        list: Object.keys(confNameTypeMap.value).map((v) => ({ label: v, value: v })),
      };
    }),
  );

  // 描述 tippy 实例
  const tippyInstances: Instance[] = [];

  const confNameTypeMap = ref<Record<string, string[]>>({});
  const availableParams = ref<ServiceReturnType<typeof getConfigNames>>([]);

  // 权限
  const permissions = ref<ServiceReturnType<typeof getConfigBaseDetails>['permission']>({
    global_dbconfig_edit: false,
  });

  // 是否为标准 DB 配置，此类配置隐藏「显示名」列
  const isStandardDbConfig = computed(() => ['dbconf', 'proxyconf'].includes(confType));

  // 数据类型过滤选项（来源：list_conf_name_types 接口的 key 列表）
  const valueTypeFilter = computed(() => ({
    component: markRaw(MultipleSelect),
    props: {
      list: Object.keys(confNameTypeMap.value).map((v) => ({
        label: v,
        value: v,
      })),
    },
    showConfirmAndReset: true,
  }));

  // 布尔型过滤选项（是/否）
  const boolFilter = {
    component: markRaw(MultipleSelect),
    props: {
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
    },
    showConfirmAndReset: true,
  };

  // 获取 confType 对应的显示名称
  useRequest(getListConfTypes, {
    defaultParams: [{ meta_cluster_type: clusterType }],
    onSuccess(res) {
      currentConfItem.value = res.find((item) => item.conf_type === confType);
    },
  });

  // 获取配置详情
  const { run: fetchDetail } = useRequest(getConfigBaseDetails, {
    manual: true,
    onSuccess(res: DetailResult) {
      permissions.value = res.permission;
      detailData.value = res;
      allConfItems.value = res.conf_items || [];
      paramTableRef.value?.fetchData({}, true);
    },
  });

  const fetchDetailData = () => {
    fetchDetail(
      { conf_type: confType, meta_cluster_type: currentConfItem.value!.namespace, version: version },
      { permission: 'catch' },
    );
  };

  // 获取数据类型与约束类型联动选项
  useRequest(getListConfNameTypes, {
    defaultParams: [{}],
    onSuccess(res) {
      confNameTypeMap.value = res;
    },
  });

  // 获取可选参数名
  const { run: fetchAvailableParams } = useRequest(getConfigNames, {
    manual: true,
    onSuccess(res) {
      availableParams.value = res;
    },
  });

  watch(
    () => currentConfItem.value?.namespace,
    (value) => {
      if (value) {
        // 初始加载详情数据（传入 permission: 'catch' 由 ApplyPermissionCatch 拦截无权限场景）
        fetchDetailData();
        fetchAvailableParams({ conf_type: confType, meta_cluster_type: value, version: version });
      }
    },
  );

  // 表格数据源（前端分页 + 过滤）
  const paramDataSource = (params: { limit: number; offset: number }) => {
    let data = allConfItems.value;

    // 搜索 + 列筛选统一过滤
    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      data = data.filter((item: Record<string, any>) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          // multiple 列筛选值为逗号分隔字符串
          if (['flag_encrypt', 'flag_readonly', 'flag_visible', 'need_restart'].includes(key)) {
            const selectedVals = val.split(',');
            if (key === 'flag_readonly') return selectedVals.includes(item.flag_readonly === 0 ? '1' : '0');
            if (key === 'flag_encrypt') return selectedVals.includes(item.flag_encrypt === 1 ? '1' : '0');
            return selectedVals.includes(String(item[key] ?? ''));
          }
          // input 搜索：模糊匹配
          const search = String(val).toLowerCase();
          const fieldValue = String(item[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    const start = params.offset;
    const end = start + params.limit;
    const result = { count: data.length, results: data.slice(start, end) };

    return Promise.resolve(result);
  };

  // 快速搜索变更
  const handleQuickSearchChange = () => {
    paramTableRef.value?.fetchData({}, true);
  };

  /** 列筛选变更：同步到 searchValue（表头显示标签） */
  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
  };

  // 新建参数
  const handleAddParam = () => {
    paramFormSliderRef.value?.openCreate();
  };

  // 编辑参数
  const handleEditParam = (row: DetailResult['conf_items'][number]) => {
    paramFormSliderRef.value?.openEdit(row, getCreateFrom(row));
  };

  /**
   * 获取参数来源（后端 create_from 字段）
   * - ''：系统定义且未修改
   * - 'def'：系统定义但平台修改成了自己的定义
   * - 'plat'：平台自定义
   */
  const getCreateFrom = (row: ParameterConfigItem): ParameterConfigItem['create_from'] => row.create_from ?? '';

  // 删除参数
  const handleDeleteParam = (row: DetailResult['conf_items'][number]) => {
    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      content: () =>
        h('div', { class: 'restore-param-content' }, [
          h('p', t('参数_xxx_将从平台定义中移除_删除后不可恢复', { name: row.conf_name })),
        ]),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: async () => {
        await changeConfNames({
          conf_file: detailData.value.version || version,
          conf_names: [
            {
              conf_name: row.conf_name,
              conf_name_lc: row.conf_name_lc ?? '',
              description: row.description ?? '',
              flag_encrypt: (row as Record<string, any>).flag_encrypt ?? 0,
              flag_locked: row.flag_locked ?? 0,
              flag_readonly: row.flag_readonly ?? 0,
              flag_visible: row.flag_visible ?? 0,
              need_restart: row.need_restart ?? 0,
              op_type: 'remove',
              value_allowed: row.value_allowed ?? '',
              value_default: row.value_default ?? '',
              value_type: row.value_type ?? '',
              value_type_sub: row.value_type_sub ?? '',
            },
          ],
          conf_type: confType,
          meta_cluster_type: currentConfItem.value!.namespace,
        });
        messageSuccess(t('删除成功'));
        fetchDetail({ conf_type: confType, meta_cluster_type: currentConfItem.value!.namespace, version: version });
      },
      title: t('确认删除该参数？'),
    });
  };

  /**
   * 恢复参数为系统初始值（仅 create_from === 'def' 可用）
   * 调用 recoverDefaultConfigItem，op_type 统一传 'remove'，后端自动判断操作类型
   */
  const handleRestoreParam = (row: DetailResult['conf_items'][number]) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('恢复初始值'),
      content: () =>
        h('div', { class: 'restore-param-content' }, [
          h('p', { class: 'mb-6' }, `${t('参数名')}：${row.conf_name}`),
          h('p', t('将参数定义恢复为系统初始配置_不影响业务已自定义的参数值')),
        ]),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: async () => {
        await changeConfNames({
          conf_file: detailData.value.version || version,
          conf_names: [
            {
              conf_name: row.conf_name,
              conf_name_lc: row.conf_name_lc ?? '',
              description: row.description ?? '',
              flag_encrypt: (row as Record<string, any>).flag_encrypt ?? 0,
              flag_locked: row.flag_locked ?? 0,
              flag_readonly: row.flag_readonly ?? 0,
              flag_visible: row.flag_visible ?? 0,
              need_restart: row.need_restart ?? 0,
              op_type: 'remove',
              value_allowed: row.value_allowed ?? '',
              value_default: row.value_default ?? '',
              value_type: row.value_type ?? '',
              value_type_sub: row.value_type_sub ?? '',
            },
          ],
          conf_type: confType,
          meta_cluster_type: currentConfItem.value!.namespace,
        });
        messageSuccess(t('操作成功_参数已恢复为初始值'));
        fetchDetail({ conf_type: confType, meta_cluster_type: currentConfItem.value!.namespace, version: version });
      },
      title: t('确认恢复为初始值？'),
    });
  };

  /** 初始化描述 tippy 提示 */
  const initDescriptionTippy = () => {
    // 销毁旧实例
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;

    nextTick(() => {
      const icons = document.querySelectorAll('.param-desc-icon');
      icons.forEach((el) => {
        const iconEl = el as HTMLElement;
        const confName = iconEl.dataset.confName || '';
        const description = iconEl.dataset.description || '';
        if (!description) return;

        const content = document.createElement('div');
        content.className = 'description-tippy-content';
        content.innerHTML = `<div class="desc-title">${confName}</div><div class="desc-text">${description}</div>`;

        const instance = dbTippy(iconEl, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: true,
          content,
          hideOnClick: false,
          interactive: false,
          placement: 'top',
          theme: 'light',
          trigger: 'mouseenter focus',
          zIndex: 9999,
        });
        tippyInstances.push(instance);
      });
    });
  };

  onUnmounted(() => {
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;
  });

  defineExpose({
    routerBack() {
      router.back();
    },
  });
</script>

<style lang="less" scoped>
  .config-detail-nav-title {
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 16px;
    line-height: 24px;
  }

  .platform-detail-content {
    padding: 24px;

    .platform-info-card {
      padding: 24px 24px 0;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);
    }
  }

  .config-detail-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .config-detail-meta {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #979ba5;

    & > span + span {
      margin-left: 8px;
    }

    &::before {
      content: '';
      display: inline-block;
      width: 1px;
      height: 14px;
      background: #dcdee5;
    }
  }

  .param-operations {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .column-title-tips {
    cursor: help;
    border-bottom: 1px dashed #979ba5;
  }

  .no-constraint-text {
    color: #c4c6cc;
  }

  .param-desc-icon {
    font-size: 14px;
    cursor: pointer;
    color: #c4c6cc;

    &:hover {
      color: #3a84ff;
    }
  }
</style>

<style lang="less">
  .description-tippy-content {
    max-width: 320px;
    padding: 12px 16px;

    .desc-title {
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #313238;
      word-break: break-all;
    }

    .desc-text {
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      word-break: break-word;
    }
  }

  .restore-param-content {
    background: #f5f7fa;
    color: #63656e;
    text-align: left;
    padding: 12px 14px;
    line-height: 1.6;
  }
</style>
