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
  <div class="platform-detail-page">
    <div class="platform-detail-content">
      <!-- 参数信息 -->
      <DbCard>
        <div class="param-operations mb-16">
          <BkButton
            theme="primary"
            @click="handleAddParam">
            {{ t('新增参数') }}
          </BkButton>
          <DbQuickSearch
            v-model="searchValue"
            :data="quickSearchData"
            :placeholder="t('搜索参数名_显示名_平台默认值_允许值_数据类型')"
            style="width: 500px; margin-left: auto"
            @change="handleQuickSearchChange" />
        </div>
        <BkLoading :loading="paramLoading">
          <DbTable
            ref="paramTableRef"
            :data-source="paramDataSource"
            row-key="conf_name"
            @clear-search="handleQuickSearchChange"
            @filter-change="handleFilterChange"
            @request-success="handleRequestSuccess">
            <TableColumn
              col-key="conf_name"
              ellipsis
              fixed="left"
              :min-width="250"
              :title="t('参数名')"
              :width="250">
              <template #default="{ row }">
                {{ row.conf_name }}
                <DbIcon
                  v-if="row.description"
                  class="param-desc-icon ml-4"
                  :data-conf-name="row.conf_name"
                  :data-description="row.description"
                  type="bk-dbm-icon db-icon-attention" />
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
                {{ row.flag_encrypt === 1 ? '******' : row.value_default }}
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
              col-key="flag_encrypt"
              :filter="boolFilter"
              :width="100">
              <template #title>
                <span
                  v-bk-tooltips="t('参数值加密存储，并在页面固定展示为 6 位星号')"
                  class="column-title-tips">
                  {{ t('加密存储') }}
                </span>
              </template>
              <template #default="{ row }">
                {{ row.flag_encrypt === 1 ? t('是') : t('否') }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="operation"
              fixed="right"
              :title="t('操作')"
              :width="120">
              <template #default="{ row }">
                <BkButton
                  class="mr-16"
                  text
                  theme="primary"
                  @click="handleEditParam(row)">
                  {{ t('编辑') }}
                </BkButton>
                <BkPopConfirm
                  :cancel-text="t('取消')"
                  :confirm-config="{ theme: 'danger' }"
                  :confirm-text="t('删除')"
                  :title="t('确认删除该参数？')"
                  trigger="click"
                  :width="275"
                  @confirm="handleDeleteParam(row)">
                  <template #content>
                    <div
                      class="mb-16"
                      style="line-height: 20px">
                      <p class="mb-6">
                        {{ t('参数名称_:_name', { name: row.conf_name }) }}
                      </p>
                      <p>
                        {{ t('删除后，将不可恢复，请谨慎操作！') }}
                      </p>
                    </div>
                  </template>
                  <span @click.stop>
                    <BkButton
                      text
                      theme="primary">
                      {{ t('删除') }}
                    </BkButton>
                  </span>
                </BkPopConfirm>
              </template>
            </TableColumn>
          </DbTable>
        </BkLoading>
      </DbCard>
    </div>

    <!-- 新增/编辑参数侧滑 -->
    <BkSideslider
      v-if="isShowAddParam"
      :is-show="isShowAddParam"
      quick-close
      width="60%"
      @closed="handleCloseSideslider">
      <template #header>
        <span>{{ isEditMode ? t('编辑参数') : t('新建参数') }}</span>
        <span
          v-if="isEditMode"
          class="sideslider-sub-title">
          {{ addParamForm.conf_name }}
        </span>
      </template>
      <div class="add-param-content">
        <BkForm
          ref="addFormRef"
          form-type="vertical"
          :model="addParamForm">
          <!-- 基础定义 -->
          <div class="form-section">
            <div class="form-section-title">{{ t('基础定义') }}</div>
            <!-- 参数名 + 参数显示名 -->
            <div class="form-row">
              <BkFormItem
                :label="t('参数名')"
                property="conf_name"
                required>
                <BkInput
                  v-model="addParamForm.conf_name"
                  :disabled="isEditMode"
                  :placeholder="t('支持字母、数字及常用符号，不允许使用「`」，最大100字符')" />
              </BkFormItem>
              <BkFormItem
                :label="t('参数显示名')"
                property="conf_name_lc">
                <BkInput
                  v-model="addParamForm.conf_name_lc"
                  :placeholder="t('请输入显示名')" />
              </BkFormItem>
            </div>
            <!-- 数据类型 + 约束类型 -->
            <div class="form-row">
              <BkFormItem
                :label="t('数据类型')"
                property="value_type"
                required>
                <BkSelect
                  v-model="addParamForm.value_type"
                  :clearable="false"
                  @change="handleValueTypeChange">
                  <BkOption
                    v-for="opt in valueTypeOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value" />
                </BkSelect>
              </BkFormItem>
              <BkFormItem
                :label="t('约束类型')"
                property="value_type_sub"
                required>
                <BkSelect
                  v-model="addParamForm.value_type_sub"
                  :clearable="false"
                  :disabled="!addParamForm.value_type"
                  @change="handleValueTypeSubChange">
                  <BkOption
                    v-for="opt in valueTypeSubOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value" />
                </BkSelect>
              </BkFormItem>
            </div>
            <!-- 允许值 -->
            <BkFormItem
              :disabled="isValueAllowedDisabled"
              :label="t('允许值')"
              property="value_allowed"
              :required="isValueAllowedRequired">
              <BkInput
                v-model="addParamForm.value_allowed"
                :disabled="isValueAllowedDisabled"
                :placeholder="isValueAllowedDisabled ? valueAllowedPlaceholder : t('请输入')" />
              <p class="form-item-tips">{{ t('填写示例') }}：{{ valueAllowedExample }}</p>
            </BkFormItem>
          </div>

          <!-- 默认值与安全 -->
          <div class="form-section">
            <div class="form-section-title">{{ t('默认值与安全') }}</div>
            <BkCheckboxGroup
              :model-value="securityCheckboxValue"
              @change="handleSecurityCheckboxChange">
              <BkCheckbox label="flag_encrypt">
                {{ t('加密存储') }}
                <span class="checkbox-desc">{{ t('参数值加密存储，并在页面固定展示为 6 位星号') }}</span>
              </BkCheckbox>
            </BkCheckboxGroup>
            <BkFormItem
              :label="t('平台默认值')"
              property="value_default"
              required>
              <div class="default-value-row">
                <BkInput
                  v-model="addParamForm.value_default"
                  :placeholder="t('请输入')"
                  :type="addParamForm.flag_encrypt ? 'password' : 'text'" />
                <BkCheckbox
                  v-if="showEmptyStringCheckbox"
                  v-model="addParamForm.flag_empty_string"
                  class="ml-8 empty-string-checkbox">
                  {{ t('设为空字符串') }}
                </BkCheckbox>
              </div>
              <p class="form-item-tips">{{ t('可为空_表示不设置平台默认值_如填写需符合允许值规则') }}</p>
            </BkFormItem>
          </div>

          <!-- 业务配置规则 -->
          <div class="form-section">
            <div class="form-section-title">{{ t('业务配置规则') }}</div>
            <BkCheckboxGroup
              :model-value="bizRuleCheckboxValue"
              @change="handleBizRuleCheckboxChange">
              <BkCheckbox label="flag_visible">
                {{ t('业务默认可见') }}
                <span class="checkbox-desc">{{
                  t('是否在业务配置页默认带出该参数；关闭后业务仍可通过「添加参数」主动加入')
                }}</span>
              </BkCheckbox>
              <BkCheckbox label="flag_readonly_inverse">
                {{ t('业务可编辑') }}
                <span class="checkbox-desc">{{ t('控制业务侧是否可编辑该参数数值') }}</span>
              </BkCheckbox>
              <BkCheckbox label="need_restart">
                {{ t('重启生效') }}
                <span class="checkbox-desc">{{
                  t('预留配置下发场景；后续下发的存量实例后，是否需要重启实例生效')
                }}</span>
              </BkCheckbox>
            </BkCheckboxGroup>
          </div>

          <!-- 参数描述 -->
          <BkFormItem :label="t('参数描述')">
            <template #label>
              {{ t('参数描述') }}
              <span class="form-section-title-tips">{{
                t('描述不在列表中单独占列_有内容时将显示为参数名后的说明图标')
              }}</span>
            </template>
            <BkInput
              v-model="addParamForm.description"
              :maxlength="100"
              :placeholder="t('请输入参数描述')"
              show-word-limit
              type="textarea" />
          </BkFormItem>
        </BkForm>
      </div>
      <template #footer>
        <BkButton
          class="mr-8"
          :loading="submitLoading"
          theme="primary"
          @click="handleAddParamConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton @click="isShowAddParam = false">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkSideslider>
  </div>
  <Teleport to="#dbContentTitleAppend">
    <div class="config-detail-header">
      <span class="config-detail-nav-title">
        {{ configTypeName }}
      </span>
      <span class="config-detail-meta">
        <span v-if="detailData.name">{{ t('配置名称') }}：{{ detailData.name }}</span>
        <span v-if="detailData.updated_by || detailData.updated_at">
          {{ t('最近更新') }}：{{ detailData.updated_by || '--' }} / {{ detailData.updated_at || '--' }}
        </span>
        <span v-if="detailData.description">{{ t('描述') }}：{{ detailData.description }}</span>
      </span>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import {
    changeConfNames,
    getConfigBaseDetails,
    getConfigNames,
    getListConfNameTypes,
    getListConfTypes,
  } from '@services/source/configs';

  import { dbTippy } from '@common/tippy';

  import DbQuickSearch from '@components/db-quick-search/Index.vue';
  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import { messageSuccess } from '@utils';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const { clusterType, confType, version } = route.params as {
    clusterType: string;
    confType: string;
    version: string;
  };

  // 无约束标识常量
  const NO_CONSTRAINT = t('无约束');

  const paramTableRef = ref<InstanceType<typeof DbTable>>();
  const addFormRef = ref();

  const configTypeName = ref('');
  type DetailResult = ServiceReturnType<typeof getConfigBaseDetails>;
  const detailData = ref<Partial<DetailResult>>({});
  const allConfItems = ref<DetailResult['conf_items']>([]);

  const paramLoading = ref(false);
  const filterValues = ref<Record<string, string[]>>({});

  // 快速搜索
  const searchValue = ref<Record<string, any>>({});
  const quickSearchData = [
    { id: 'conf_name', name: t('参数名'), type: 'input' as const },
    { id: 'conf_name_lc', name: t('显示名'), type: 'input' as const },
    { id: 'value_default', name: t('平台默认值'), type: 'input' as const },
    { id: 'value_allowed', name: t('允许值'), type: 'input' as const },
    { id: 'value_type', name: t('数据类型'), type: 'input' as const },
  ];

  const isShowAddParam = ref(false);
  const isEditMode = ref(false);
  const submitLoading = ref(false);

  // 描述 tippy 实例
  const tippyInstances: Instance[] = [];

  // 新增/编辑表单
  const addParamForm = reactive({
    conf_name: '',
    conf_name_lc: '',
    description: '',
    flag_empty_string: false,
    flag_encrypt: false,
    flag_readonly_inverse: true, // UI 展示反转：勾选=业务可修改 → flag_readonly=0
    flag_visible: true, // 默认勾选：业务默认可见
    need_restart: false,
    value_allowed: '',
    value_default: '',
    value_type: '',
    value_type_sub: '',
  });

  const confNameTypeMap = ref<Record<string, string[]>>({});
  const availableParams = ref<ServiceReturnType<typeof getConfigNames>>([]);

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

  // 数据类型选项（接口返回的 key 列表）
  const valueTypeOptions = computed(() => Object.keys(confNameTypeMap.value).map((v) => ({ label: v, value: v })));

  // 约束类型选项（根据选中的数据类型过滤，仅 STRING 类型可选无约束）
  const valueTypeSubOptions = computed(() => {
    if (!addParamForm.value_type) return [];
    const isString = addParamForm.value_type === 'STRING';
    const list = (confNameTypeMap.value[addParamForm.value_type] || [])
      .filter((v) => {
        // STRING 类型下隐藏 STRING 选项（它和空字符串/无约束是一个意思）
        if (isString && v === 'STRING') return false;
        // 非 STRING 类型过滤掉空字符串（无约束选项）
        return isString || v;
      })
      .map((v) => ({
        label: v || NO_CONSTRAINT,
        value: v || NO_CONSTRAINT,
      }));
    return list.sort((a, b) => {
      if (a.value === NO_CONSTRAINT && b.value !== NO_CONSTRAINT) return 1;
      if (a.value !== NO_CONSTRAINT && b.value === NO_CONSTRAINT) return -1;
      return 0;
    });
  });

  // 安全组 Checkbox（加密存储）
  const securityCheckboxValue = computed(() => {
    const keys: (keyof typeof addParamForm & string)[] = ['flag_encrypt'];
    return keys.filter((key) => addParamForm[key]);
  });
  // 业务配置规则 Checkbox
  const bizRuleCheckboxKeys = ['flag_visible', 'flag_readonly_inverse', 'need_restart'] as const;
  const bizRuleCheckboxValue = computed(() => bizRuleCheckboxKeys.filter((key) => addParamForm[key]));

  // 不需要填写允许值的约束类型（由后端校验合法性）
  const NO_VALUE_ALLOWED_TYPES = ['JSON', 'MAP', 'LIST', 'REGEX', 'GOVALIDATE', NO_CONSTRAINT];

  // 允许值字段状态
  const isValueAllowedDisabled = computed(() => NO_VALUE_ALLOWED_TYPES.includes(addParamForm.value_type_sub));
  const isValueAllowedRequired = computed(() => !NO_VALUE_ALLOWED_TYPES.includes(addParamForm.value_type_sub));

  // 是否显示"设为空字符串"复选框：STRING + 无约束 + 未加密
  const showEmptyStringCheckbox = computed(
    () =>
      addParamForm.value_type === 'STRING' &&
      addParamForm.value_type_sub === NO_CONSTRAINT &&
      !addParamForm.flag_encrypt,
  );

  watch(
    () => addParamForm.flag_empty_string,
    (val) => {
      if (val) {
        addParamForm.value_default = '';
      }
    },
  );

  // 允许值置灰时的占位文字
  const valueAllowedPlaceholder = computed(() => {
    const placeholderMap: Record<string, string> = {
      GOVALIDATE: t('合法的 validator 标签'),
      JSON: t('合法的 JSON'),
      LIST: t('合法的 JSON 数组'),
      MAP: t('合法的 JSON 对象'),
      REGEX: t('合法的正则表达式'),
    };
    return placeholderMap[addParamForm.value_type_sub] || t('无约束');
  });

  // 允许值填写示例（根据数据类型 + 约束类型组合）
  const valueAllowedExample = computed(() => {
    const key = `${addParamForm.value_type}_${addParamForm.value_type_sub}`;
    const exampleMap: Record<string, string> = {
      BOOL_ENUM: t(
        '填写示例：ON|OFF / true|false / 1|0；本质是 2 个候选值的 ENUM，候选值以「|」分隔，业务取值仅能单选',
      ),
      FLOAT_ENUM: t('填写示例：0.1|0.5|1.0；候选值以「|」分隔，业务取值仅能单选'),
      FLOAT_RANGE: t('填写示例：[0.0,1.0]；格式 [min,max]，业务取值需满足 min ≤ 值 ≤ max（两端均包含）'),
      INT_ENUM: t('填写示例：1|4|8；候选值以「|」分隔，业务取值仅能单选'),
      INT_RANGE: t('填写示例：[0,99]；格式 [min,max]，业务取值需满足 min ≤ 值 ≤ max（两端均包含）'),
      NUMBER_ENUM: t('填写示例：1|4|8；候选值以「|」分隔，业务取值仅能单选'),
      NUMBER_RANGE: t('填写示例：[0,99]；格式 [min,max]，业务取值需满足 min ≤ 值 ≤ max（两端均包含）'),
      STRING_BYTES: t('填写示例：[1024,1g]；单位 k(KB) / m(MB) / g(GB)，无单位则为字节'),
      STRING_DURATION: t('填写示例：[1m,60m]；单位 s(秒) / m(分) / h(小时) / d(天 = 24 小时)'),
      STRING_ENUM: t('填写示例：ROW|MIXED|STATEMENT；候选值以「|」分隔，业务取值仅能单选'),
      STRING_ENUMS: t('填写示例：read,write,admin；候选值以英文「,」分隔，业务取值可多选'),
    };
    return exampleMap[key] || '--';
  });

  // 获取 confType 对应的显示名称
  useRequest(getListConfTypes, {
    defaultParams: [{ meta_cluster_type: clusterType }],
    onSuccess(res) {
      const matched = res.find((item) => item.conf_type === confType);
      configTypeName.value = matched?.name || confType;
    },
  });

  // 获取配置详情
  const { run: fetchDetail } = useRequest(getConfigBaseDetails, {
    defaultParams: [{ conf_type: confType, meta_cluster_type: clusterType, version: version }],
    onSuccess(res) {
      detailData.value = res;
      allConfItems.value = res.conf_items || [];
      paramTableRef.value?.fetchData({}, true);
      // 延迟等待表格异步渲染完成后再初始化 tippy
      setTimeout(() => initDescriptionTippy(), 300);
    },
  });

  // 获取数据类型与约束类型联动选项
  useRequest(getListConfNameTypes, {
    defaultParams: [{}],
    onSuccess(res) {
      confNameTypeMap.value = res;
    },
  });

  // 获取可选参数名
  useRequest(getConfigNames, {
    defaultParams: [{ conf_type: confType, meta_cluster_type: clusterType, version: version }],
    onSuccess(res) {
      availableParams.value = res;
    },
  });

  // 表格数据源（前端分页 + 过滤）
  const paramDataSource = (params: { limit: number; offset: number }) => {
    let data = allConfItems.value;

    // 快速搜索过滤
    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      data = data.filter((item: Record<string, any>) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          const search = String(val).toLowerCase();
          const fieldValue = String(item[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    // 列筛选过滤
    Object.entries(filterValues.value).forEach(([key, values]) => {
      if (!values || values.length === 0) return;
      data = data.filter((item: Record<string, any>) => {
        if (key === 'flag_readonly') return values.includes(item.flag_readonly === 0 ? '1' : '0');
        if (key === 'flag_encrypt') return values.includes(item.flag_encrypt === 1 ? '1' : '0');
        if (['flag_visible', 'need_restart'].includes(key)) return values.includes(String(item[key]));
        return values.includes(item[key] || '');
      });
    });

    const start = params.offset;
    const end = start + params.limit;
    return Promise.resolve({ count: data.length, results: data.slice(start, end) });
  };

  // 快速搜索变更
  const handleQuickSearchChange = () => {
    paramTableRef.value?.fetchData({}, true);
    setTimeout(() => initDescriptionTippy(), 300);
  };

  // 过滤变更
  const handleFilterChange = (filters: Record<string, string[]>) => {
    filterValues.value = filters;
    nextTick(() => paramTableRef.value?.fetchData({}, true));
    setTimeout(() => initDescriptionTippy(), 300);
  };

  /** 数据请求成功后重新初始化 tippy（含分页切换场景） */
  const handleRequestSuccess = () => {
    setTimeout(() => initDescriptionTippy(), 100);
  };

  // 数据类型变更：清空约束类型和允许值
  const handleValueTypeChange = () => {
    addParamForm.value_type_sub = '';
    addParamForm.value_allowed = '';
  };

  // 约束类型选项变更：仅剩一项时自动选中（如 BOOL→ENUM，STRING→无约束）
  watch(
    () => valueTypeSubOptions.value,
    (options) => {
      if (options.length === 1 && !addParamForm.value_type_sub) {
        addParamForm.value_type_sub = options[0].value;
      }
    },
  );

  // 约束类型变更：切换到不需要允许值的类型时清空允许值
  const handleValueTypeSubChange = (value: string) => {
    if (NO_VALUE_ALLOWED_TYPES.includes(value) && addParamForm.value_allowed) {
      addParamForm.value_allowed = '';
    }
  };

  // 安全组 Checkbox 变更（加密存储）
  const handleSecurityCheckboxChange = (values: string[]) => {
    addParamForm.flag_encrypt = values.includes('flag_encrypt');
  };

  // 业务配置规则 Checkbox 变更
  const handleBizRuleCheckboxChange = (values: string[]) => {
    bizRuleCheckboxKeys.forEach((key) => {
      addParamForm[key] = values.includes(key) as never;
    });
  };

  // 新建参数
  const handleAddParam = () => {
    isEditMode.value = false;
    Object.assign(addParamForm, {
      conf_name: '',
      conf_name_lc: '',
      description: '',
      flag_empty_string: false,
      flag_encrypt: false,
      flag_readonly_inverse: true,
      flag_visible: true,
      need_restart: false,
      value_allowed: '',
      value_default: '',
      value_type: '',
      value_type_sub: '',
    });
    isShowAddParam.value = true;
  };

  // 关闭侧栏
  const handleCloseSideslider = () => {
    isShowAddParam.value = false;
    isEditMode.value = false;
  };

  // 提交新建/编辑参数
  const handleAddParamConfirm = async () => {
    try {
      await addFormRef.value?.validate();
    } catch {
      return;
    }

    submitLoading.value = true;
    try {
      await changeConfNames({
        conf_file: detailData.value.version || version,
        conf_names: [
          {
            conf_name: addParamForm.conf_name,
            conf_name_lc: addParamForm.conf_name_lc,
            description: addParamForm.description,
            flag_encrypt: addParamForm.flag_encrypt ? 1 : 0,
            flag_readonly: addParamForm.flag_readonly_inverse ? 0 : 1,
            flag_visible: addParamForm.flag_visible ? 1 : 0,
            need_restart: addParamForm.need_restart ? 1 : 0,
            op_type: isEditMode.value ? 'update' : 'add',
            value_allowed: addParamForm.value_allowed,
            value_default: addParamForm.value_default,
            value_type: addParamForm.value_type,
            value_type_sub: addParamForm.value_type_sub === NO_CONSTRAINT ? '' : addParamForm.value_type_sub,
          },
        ],
        conf_type: confType,
        meta_cluster_type: clusterType,
      });
      isShowAddParam.value = false;
      messageSuccess(isEditMode.value ? t('编辑成功') : t('新增成功'));
      isEditMode.value = false;
      fetchDetail({ conf_type: confType, meta_cluster_type: clusterType, version: version });
    } finally {
      submitLoading.value = false;
    }
  };

  // 编辑参数
  const handleEditParam = (row: DetailResult['conf_items'][number]) => {
    isEditMode.value = true;
    Object.assign(addParamForm, {
      conf_name: row.conf_name,
      conf_name_lc: row.conf_name_lc ?? '',
      description: row.description,
      // 历史兼容：STRING 类型的约束类型为 STRING 时，等同于无约束
      flag_empty_string:
        !row.value_default && row.value_type === 'STRING' && (!row.value_type_sub || row.value_type_sub === 'STRING'),
      flag_encrypt: row.flag_encrypt === 1,
      flag_readonly_inverse: row.flag_readonly === 0,
      flag_visible: row.flag_visible === 1,
      need_restart: row.need_restart === 1,
      value_allowed: row.value_allowed ?? '',
      value_default: row.value_default ?? '',
      value_type: row.value_type ?? '',
      // 历史兼容：STRING 类型的约束类型为 STRING 时，等同于无约束
      value_type_sub: row.value_type_sub === 'STRING' ? NO_CONSTRAINT : (row.value_type_sub ?? ''),
    });
    isShowAddParam.value = true;
  };

  // 删除参数
  const handleDeleteParam = async (row: DetailResult['conf_items'][number]) => {
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
      meta_cluster_type: clusterType,
    });
    messageSuccess(t('删除成功'));
    fetchDetail({ conf_type: confType, meta_cluster_type: clusterType, version: version });
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
      router.push({ name: 'PlatformDbConfigureList' });
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
    border-radius: 2px;

    :deep(.db-card) {
      padding-bottom: 0;
    }

    :deep(.db-card-content) {
      padding-top: 0;
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

  .add-param-content {
    padding: 24px;

    .form-section {
      margin-bottom: 24px;
      padding: 16px 20px;
      background: #fafbfd;
      border-radius: 2px;
    }

    .form-section + .form-section {
      margin-top: 0;
    }

    .form-section-title {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 16px;
      font-size: 14px;
      font-weight: 600;
      color: #313238;
    }

    .form-section-title-tips {
      margin-left: 4px;
      font-weight: normal;
      font-size: 12px;
      color: #979ba5;
    }

    .form-row {
      display: flex;
      gap: 16px;

      :deep(.bk-form-item) {
        flex: 1;
      }
    }

    .form-item-tips {
      margin-top: 4px;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
    }

    .default-value-row {
      display: flex;
      align-items: center;

      .empty-string-checkbox {
        white-space: nowrap;
        flex-shrink: 0;
      }
    }

    :deep(.bk-checkbox-group) {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 24px;
    }

    :deep(.bk-checkbox ~ .bk-checkbox) {
      margin-left: 0;
    }

    .checkbox-desc {
      font-size: 12px;
      color: #979ba5;
      margin-left: 4px;
    }
  }

  .sideslider-sub-title {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-size: 14px;
    font-weight: normal;
    color: #979ba5;

    &::before {
      position: absolute;
      top: 50%;
      left: 0;
      width: 1px;
      height: 14px;
      content: '';
      background: #dcdee5;
      transform: translateY(-50%);
    }
  }

  .bool-icon-yes,
  .bool-icon-no {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
  }

  .bool-icon-yes {
    font-size: 12px;
    color: #65c389;
    background: #ebfaf0;
  }

  .bool-icon-no {
    font-size: 16px;
    color: #ff5656;
    background: #ffebeb;
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
</style>
