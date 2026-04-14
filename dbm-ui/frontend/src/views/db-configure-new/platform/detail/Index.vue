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
    <div class="platform-detail-content db-scroll-y">
      <!-- 基础信息 -->
      <DbCard
        mode="collapse"
        :title="t('基础信息')">
        <BkLoading :loading="loading">
          <BkForm class="base-info-form">
            <div class="base-info-form-row">
              <BkFormItem :label="t('配置名称')">
                {{ detailData.name || '--' }}
              </BkFormItem>
              <BkFormItem :label="t('配置文件')">
                {{ detailData.version || '--' }}
              </BkFormItem>
            </div>
            <div class="base-info-form-row">
              <BkFormItem :label="t('最近更新人')">
                {{ detailData.updated_by || '--' }}
              </BkFormItem>
              <BkFormItem :label="t('更新时间')">
                {{ detailData.updated_at || '--' }}
              </BkFormItem>
            </div>
            <div class="base-info-form-row">
              <BkFormItem :label="t('描述')">
                {{ detailData.description || '--' }}
              </BkFormItem>
            </div>
          </BkForm>
        </BkLoading>
      </DbCard>

      <!-- 参数信息 -->
      <DbCard
        class="mt-16"
        mode="collapse"
        :title="t('参数信息')">
        <div class="param-operations mb-16">
          <BkButton
            theme="primary"
            @click="handleAddParam">
            {{ t('新增参数') }}
          </BkButton>
        </div>
        <BkLoading :loading="paramLoading">
          <DbTable
            ref="paramTableRef"
            :data-source="paramDataSource"
            fixed-pagination
            row-key="conf_name"
            @filter-change="handleFilterChange">
            <TableColumn
              col-key="conf_name"
              ellipsis
              :title="t('参数名')"
              :width="160" />
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
              :title="t('默认值')"
              :width="180">
              <template #default="{ row }">
                {{ row.value_default ?? '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="value_allowed"
              :title="t('允许值')"
              :width="220">
              <template #default="{ row }">
                <template v-if="row.value_type_sub">
                  <BkTag v-if="row.value_type_sub">{{ row.value_type_sub }}</BkTag>
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
                <BkTag
                  v-if="row.value_type"
                  :theme="
                    (valueTypeThemeMap[row.value_type] as '' | 'success' | 'warning' | 'danger' | 'info') || 'info'
                  ">
                  {{ row.value_type }}
                </BkTag>
                <span v-else>--</span>
              </template>
            </TableColumn>
            <TableColumn
              col-key="flag_disable"
              :filter="boolFilter"
              :width="100">
              <template #title>
                <span
                  v-bk-tooltips="t('在业务空间下是否可调整参数值')"
                  class="column-title-tips">
                  {{ t('业务可修改') }}
                </span>
              </template>
              <template #default="{ row }">
                {{ row.flag_disable === 0 ? t('是') : t('否') }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="need_restart"
              :filter="boolFilter"
              :width="100">
              <template #title>
                <span
                  v-bk-tooltips="t('修改参数值后是否需要重启进程')"
                  class="column-title-tips">
                  {{ t('重启生效') }}
                </span>
              </template>
              <template #default="{ row }">
                {{ row.need_restart === 1 ? t('是') : t('否') }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="flag_locked"
              :filter="boolFilter"
              :width="100">
              <template #title>
                <span
                  v-bk-tooltips="t('生成配置是否将参数写入到配置文件')"
                  class="column-title-tips">
                  {{ t('写入配置文件') }}
                </span>
              </template>
              <template #default="{ row }">
                {{ row.flag_locked === 1 ? t('是') : t('否') }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="extra_info"
              :filter="boolFilter"
              :width="100">
              <template #title>
                <span
                  v-bk-tooltips="t('参数值显示为*号')"
                  class="column-title-tips">
                  {{ t('值加密') }}
                </span>
              </template>
              <template #default="{ row }">
                {{ row.extra_info === 'encrypt' ? t('是') : t('否') }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="operation"
              fixed="right"
              :title="t('操作')"
              :width="120">
              <template #default="{ row }">
                <BkButton
                  class="mr-8"
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
              :placeholder="t('请输入')" />
            <p class="form-item-tips">{{ t('填写示例') }}：{{ valueAllowedExample }}</p>
          </BkFormItem>
          <!-- 默认值 -->
          <BkFormItem
            :label="t('默认值')"
            property="value_default">
            <BkInput
              v-model="addParamForm.value_default"
              :placeholder="t('请输入')" />
          </BkFormItem>
          <!-- 复选框 -->
          <BkCheckboxGroup
            :model-value="checkboxGroupValue"
            @change="handleCheckboxGroupChange">
            <BkCheckbox label="flag_locked">
              {{ t('写入配置文件') }}
              <span class="checkbox-desc">（{{ t('生成配置是否将参数写入到配置文件') }}）</span>
            </BkCheckbox>
            <BkCheckbox label="flag_disable_inverse">
              {{ t('业务可修改') }}
              <span class="checkbox-desc">（{{ t('在业务空间下是否可调整参数值') }}）</span>
            </BkCheckbox>
            <BkCheckbox label="need_restart">
              {{ t('重启生效') }}
              <span class="checkbox-desc">（{{ t('修改参数值后是否需要重启进程') }}）</span>
            </BkCheckbox>
            <BkCheckbox label="value_encrypt">
              {{ t('值加密') }}
              <span class="checkbox-desc">（{{ t('参数值显示为*号') }}）</span>
            </BkCheckbox>
          </BkCheckboxGroup>
          <!-- 描述 -->
          <BkFormItem :label="t('描述')">
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
    <span class="config-detail-nav-title">
      {{ configTypeName }}
    </span>
    <span class="config-detail-nav-desc">
      {{ detailData.name || '' }}
    </span>
  </Teleport>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import {
    changeConfNames,
    getConfigBaseDetails,
    getConfigNames,
    getListConfNameTypes,
    getListConfTypes,
    validateConfItems,
  } from '@services/source/configs';

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

  const isShowAddParam = ref(false);
  const isEditMode = ref(false);
  const submitLoading = ref(false);

  // 新增/编辑表单
  const addParamForm = reactive({
    conf_name: '',
    conf_name_lc: '',
    description: '',
    flag_disable_inverse: true, // UI 展示反转：勾选=业务可修改 → flag_disable=0
    flag_locked: true, // 默认勾选：写入配置文件
    need_restart: false,
    value_allowed: '',
    value_default: '',
    value_encrypt: false,
    value_type: '',
    value_type_sub: '',
  });

  const confNameTypeMap = ref<Record<string, string[]>>({});
  const availableParams = ref<ServiceReturnType<typeof getConfigNames>>([]);

  // 是否为标准 DB 配置，此类配置隐藏「显示名」列
  const isStandardDbConfig = computed(() => ['dbconf', 'proxyconf'].includes(confType));

  // 数据类型对应的 Tag theme
  const valueTypeThemeMap: Record<string, string> = {
    BOOL: '',
    FLOAT: 'success',
    INT: 'warning',
    NUMBER: 'danger',
    STRING: 'info',
  };

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

  // 约束类型选项（根据选中的数据类型过滤，[无约束] 排最后）
  const valueTypeSubOptions = computed(() => {
    if (!addParamForm.value_type) return [];
    const list = (confNameTypeMap.value[addParamForm.value_type] || []).map((v) => ({
      label: v || NO_CONSTRAINT,
      value: v || NO_CONSTRAINT,
    }));
    return list.sort((a, b) => {
      if (a.value === NO_CONSTRAINT && b.value !== NO_CONSTRAINT) return 1;
      if (a.value !== NO_CONSTRAINT && b.value === NO_CONSTRAINT) return -1;
      return 0;
    });
  });

  // CheckboxGroup 双向绑定
  const checkboxKeys = ['flag_locked', 'flag_disable_inverse', 'need_restart', 'value_encrypt'] as const;
  const checkboxGroupValue = computed(() => checkboxKeys.filter((key) => addParamForm[key]));

  // 允许值字段状态
  const isValueAllowedDisabled = computed(() => addParamForm.value_type_sub === NO_CONSTRAINT);
  const isValueAllowedRequired = computed(() => addParamForm.value_type_sub !== NO_CONSTRAINT);

  // 允许值填写示例
  const valueAllowedExample = computed(() => {
    const exampleMap: Record<string, string> = {
      ENUM: 'ON| OFF',
      ENUMS: 'TABLE_SCAN,INDEX_SCAN',
      RANGE: '[1, 1000]',
      REGEX: '.*',
    };
    return exampleMap[addParamForm.value_type_sub] || '--';
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
  const { loading, run: fetchDetail } = useRequest(getConfigBaseDetails, {
    defaultParams: [{ conf_type: confType, meta_cluster_type: clusterType, version: version }],
    onSuccess(res) {
      detailData.value = res;
      allConfItems.value = res.conf_items || [];
      nextTick(() => paramTableRef.value?.fetchData({}, true));
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

    Object.entries(filterValues.value).forEach(([key, values]) => {
      if (!values || values.length === 0) return;
      data = data.filter((item: Record<string, any>) => {
        if (key === 'flag_disable') return values.includes(item.flag_disable === 0 ? '1' : '0');
        if (key === 'extra_info') return values.includes(item.extra_info === 'encrypt' ? '1' : '0');
        if (['flag_locked', 'need_restart'].includes(key)) return values.includes(String(item[key]));
        return values.includes(item[key] || '');
      });
    });

    const start = params.offset;
    const end = start + params.limit;
    return Promise.resolve({ count: data.length, results: data.slice(start, end) });
  };

  // 过滤变更
  const handleFilterChange = (filters: Record<string, string[]>) => {
    filterValues.value = filters;
    nextTick(() => paramTableRef.value?.fetchData({}, true));
  };

  // 数据类型变更：清空约束类型和允许值
  const handleValueTypeChange = () => {
    addParamForm.value_type_sub = '';
    addParamForm.value_allowed = '';
  };

  // 约束类型选择前校验：允许值有值时阻止选 [无约束]
  const handleValueTypeSubChange = (value: string) => {
    if (value === NO_CONSTRAINT && addParamForm.value_allowed) {
      addParamForm.value_allowed = '';
    }
  };

  // CheckboxGroup 变更
  const handleCheckboxGroupChange = (values: string[]) => {
    checkboxKeys.forEach((key) => {
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
      flag_disable_inverse: true,
      flag_locked: true,
      need_restart: false,
      value_allowed: '',
      value_default: '',
      value_encrypt: false,
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

    // 后端校验合法性（Body 直接传数组）
    try {
      await validateConfItems([
        {
          conf_name: addParamForm.conf_name,
          flag_readonly: 0,
          op_type: isEditMode.value ? 'update' : 'add',
          value_allowed: addParamForm.value_allowed,
          value_default: addParamForm.value_default,
          value_type: addParamForm.value_type,
          value_type_sub: addParamForm.value_type_sub === NO_CONSTRAINT ? '' : addParamForm.value_type_sub,
        },
      ]);
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
            flag_locked: addParamForm.flag_locked ? 1 : 0,
            flag_readonly: addParamForm.flag_disable_inverse ? 0 : 1,
            flag_visible: 1,
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
      flag_disable_inverse: row.flag_disable === 0,
      flag_locked: row.flag_locked === 1,
      need_restart: row.need_restart === 1,
      value_allowed: row.value_allowed ?? '',
      value_default: row.value_default ?? '',
      value_encrypt: row.extra_info === 'encrypt',
      value_type: row.value_type ?? '',
      value_type_sub: row.value_type_sub ?? '',
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
          description: row.description || '',
          flag_locked: 0,
          flag_readonly: 0,
          flag_visible: 1,
          need_restart: 0,
          op_type: 'remove',
          value_allowed: '',
          value_default: '',
          value_type: '',
          value_type_sub: '',
        },
      ],
      conf_type: confType,
      meta_cluster_type: clusterType,
    });
    messageSuccess(t('删除成功'));
    fetchDetail({ conf_type: confType, meta_cluster_type: clusterType, version: version });
  };

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

  .config-detail-nav-desc {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-family: 'Microsoft YaHei', sans-serif;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;
  }

  .config-detail-nav-desc::before {
    position: absolute;
    top: 50%;
    left: 0;
    width: 1px;
    height: 16px;
    content: '';
    background: #dcdee5;
    transform: translateY(-50%);
  }

  .platform-detail-content {
    height: calc(100vh - var(--notice-height) - 100px);
    padding: 24px;
  }

  .base-info-form {
    display: flex;
    flex-direction: column;
    padding: 16px 24px;
    background: #fff;
    border-radius: 2px;
  }

  .base-info-form-row {
    display: flex;
    width: 100%;

    :deep(.bk-form-item) {
      flex: 1;
      margin-bottom: 0;
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
    }
  }

  .sideslider-sub-title {
    position: relative;
    padding-left: 8px;
    margin-left: 8px;
    font-size: 12px;
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
</style>
