<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the specific language governing permissions and limitations under the License.
-->

<template>
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
        :model="addParamForm"
        :rules="formRules">
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
                :maxlength="100"
                :placeholder="t('请输入参数名')"
                show-word-limit
                @change="markDirty" />
              <div
                v-if="isConfNameAllowed"
                class="form-item-tips">
                {{ t('仅支持字母、数字、连字符、下划线、点号') }}
              </div>
            </BkFormItem>
            <BkFormItem
              :label="t('参数显示名')"
              property="conf_name_lc">
              <BkInput
                v-model="addParamForm.conf_name_lc"
                :maxlength="100"
                :placeholder="t('请输入参数显示名')"
                show-word-limit
                @change="markDirty" />
              <div
                v-if="isConfNameLcAllowed"
                class="form-item-tips">
                {{ t('支持中文、字母、数字、空格，及连字符、下划线、点号，创建后可修改') }}
              </div>
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
                @change="
                  () => {
                    handleValueTypeChange();
                    markDirty();
                  }
                ">
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
                @change="
                  (val: string) => {
                    handleValueTypeSubChange(val);
                    markDirty();
                  }
                ">
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
              :placeholder="isValueAllowedDisabled ? valueAllowedPlaceholder : t('请输入')"
              @change="markDirty" />
            <p
              v-if="valueAllowedExample"
              class="form-item-tips">
              {{ valueAllowedExample }}
            </p>
          </BkFormItem>
        </div>

        <!-- 默认值与安全 -->
        <div class="form-section">
          <div class="form-section-title">{{ t('默认值') }}</div>
          <BkFormItem
            :key="`default-${addParamForm.flag_empty_string}`"
            :label="t('平台默认值')"
            property="value_default"
            :required="!addParamForm.flag_empty_string">
            <div class="default-value-row">
              <BkInput
                v-model="addParamForm.value_default"
                :disabled="addParamForm.flag_empty_string"
                :placeholder="addParamForm.flag_empty_string ? t('空字符串') : t('请输入')"
                @change="markDirty" />
              <BkCheckbox
                v-if="showEmptyStringCheckbox"
                v-model="addParamForm.flag_empty_string"
                class="ml-8 empty-string-checkbox"
                @change="markDirty">
                {{ t('设为空字符串') }}
              </BkCheckbox>
            </div>
            <p class="form-item-tips">{{ defaultValueHint }}</p>
          </BkFormItem>
        </div>

        <!-- 业务配置规则 -->
        <div class="form-section">
          <div class="form-section-title">{{ t('业务配置规则') }}</div>
          <BkCheckboxGroup
            :model-value="bizRuleCheckboxValue"
            @change="
              (val: string[]) => {
                handleBizRuleCheckboxChange(val);
                markDirty();
              }
            ">
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
              <span class="checkbox-desc">{{ t('预留配置下发场景；后续下发的存量实例后，是否需要重启实例生效') }}</span>
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
            type="textarea"
            @change="markDirty" />
        </BkFormItem>
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        v-bk-tooltips="{
          disabled: isAddParamFormDirty,
          content: t('当前无变更，请先修改内容'),
        }"
        class="mr-8"
        :disabled="!isAddParamFormDirty"
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
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { changeConfNames } from '@services/source/configs';

  import { messageSuccess } from '@utils';

  interface Props {
    /** 集群类型 */
    clusterType: string;
    /** 数据类型 → 约束类型映射（来自 list_conf_name_types 接口） */
    confNameTypeMap: Record<string, string[]>;
    /** 配置类型，如 dbconf / proxyconf */
    confType: string;
    /** 版本号 */
    version: string;
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: 'ParamFormSideslider',
  });

  const props = withDefaults(defineProps<Props>(), {});
  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  // 无约束标识常量
  const NO_CONSTRAINT = t('无约束');

  const addFormRef = ref();

  const isShowAddParam = ref(false);
  const isEditMode = ref(false);
  const submitLoading = ref(false);

  // 新增/编辑表单
  const addParamForm = reactive({
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

  /** 表单是否有修改（任一字段变更即置位，不复位） */
  const isAddParamFormDirty = ref(false);

  /** 标记表单为已修改 */
  const markDirty = () => {
    isAddParamFormDirty.value = true;
  };

  // 数据类型选项（接口返回的 key 列表）
  const valueTypeOptions = computed(() => Object.keys(props.confNameTypeMap).map((v) => ({ label: v, value: v })));

  // 约束类型选项（根据选中的数据类型过滤，仅 STRING 类型可选无约束）
  const valueTypeSubOptions = computed(() => {
    if (!addParamForm.value_type) return [];
    const isString = addParamForm.value_type === 'STRING';
    const list = (props.confNameTypeMap[addParamForm.value_type] || [])
      .filter((v) => {
        if (isString && v === 'STRING') return false;
        return isString || v;
      })
      .map((v) => ({
        label: v || NO_CONSTRAINT,
        value: v || NO_CONSTRAINT,
      }));
    return list.sort((a, b) => {
      if (a.value === NO_CONSTRAINT && b.value !== NO_CONSTRAINT) return -1;
      if (a.value !== NO_CONSTRAINT && b.value === NO_CONSTRAINT) return 1;
      return 0;
    });
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

  // 平台默认值的动态提示文案
  const defaultValueHint = computed(() => {
    if (addParamForm.flag_empty_string) return t('平台默认值为显式空字符串');

    const vt = addParamForm.value_type;
    const vts = addParamForm.value_type_sub;

    if (vt === 'STRING' && (vts === NO_CONSTRAINT || !vts)) {
      return t('任意STRING值均可_可勾选「设为空字符串」将默认值显式置为空串');
    }

    if (vt === 'STRING' && ['GOVALIDATE', 'JSON', 'LIST', 'MAP', 'REGEX'].includes(vts)) {
      return t('需符合STRING类型_保存时由后端按约束类型校验合法性', { constraintType: vts });
    }

    return t('需符合允许值范围_不符规则保存将失败');
  });

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

  // 允许值填写示例
  const valueAllowedExample = computed(() => {
    const key = `${addParamForm.value_type}_${addParamForm.value_type_sub}`;
    const exampleMap: Record<string, string> = {
      BOOL_ENUM: t('填写示例_BOOL_ENUM'),
      FLOAT_ENUM: t('填写示例_FLOAT_ENUM'),
      FLOAT_RANGE: t('填写示例_FLOAT_RANGE'),
      INT_ENUM: t('填写示例_INT_ENUM'),
      INT_RANGE: t('填写示例_INT_RANGE'),
      NUMBER_ENUM: t('填写示例_NUMBER_ENUM'),
      NUMBER_RANGE: t('填写示例_NUMBER_RANGE'),
      STRING_BYTES: t('填写示例_STRING_BYTES'),
      STRING_DURATION: t('填写示例_STRING_DURATION'),
      STRING_ENUM: t('填写示例_STRING_ENUM'),
      STRING_ENUMS: t('填写示例_STRING_ENUMS'),
    };
    return exampleMap[key];
  });

  const isConfNameAllowed = ref(true);
  const isConfNameLcAllowed = ref(true);

  // 表单验证规则
  const formRules = {
    conf_name: [
      {
        message: '',
        required: true,
        trigger: 'blur',
        validator: (value: string) => {
          if (value) return true;
          return '';
        },
      },
      {
        message: t('格式不正确，请勿使用中文'),
        trigger: 'blur',
        validator: (value: string) => {
          // 包含中文时校验失败
          if (value && /[\u4e00-\u9fff\u3400-\u4dbf]/.test(value)) {
            isConfNameAllowed.value = false;
            return false;
          }
          return true;
        },
      },
      {
        message: t('格式不正确，请勿使用空格或特殊符号'),
        trigger: 'blur',
        validator: (value: string) => {
          // 包含空格或反引号时校验失败
          if (value && /[\s`]/.test(value)) {
            isConfNameAllowed.value = false;
            return false;
          }
          return true;
        },
      },
      // 唯一性校验（需调用接口，根据实际接口补充）
      // {
      //   message: t('该参数名已存在'),
      //   trigger: 'blur',
      //   validator: async (value: string) => {
      //     if (!value) return true;
      //     const res = await checkConfNameUnique({ conf_name: value, ... });
      //     return res.isUnique;
      //   },
      // },
    ],
    conf_name_lc: [
      {
        message: t('格式不正确，请勿使用特殊符号'),
        trigger: 'blur',
        validator: (value: string) => {
          // 参数显示名是可选的，仅当有输入时才触发校验
          if (!value) {
            return true;
          }
          // 参数显示名校验正则：支持中文、字母、数字、空格，及连字符、下划线、点号
          if (/^[\u4e00-\u9fff\u3400-\u4dbf0-9A-Za-z._\-\s]+$/.test(value)) {
            return true;
          }
          isConfNameLcAllowed.value = false;
          return false;
        },
      },
    ],
  };

  // 数据类型变更：BOOL 自动选中 ENUM；STRING 自动选中"无约束"；其它类型留空
  const handleValueTypeChange = () => {
    const vt = addParamForm.value_type;
    if (vt === 'BOOL') {
      addParamForm.value_type_sub = 'ENUM';
      addParamForm.value_allowed = '';
    } else if (vt === 'STRING') {
      addParamForm.value_type_sub = NO_CONSTRAINT;
      addParamForm.value_allowed = '';
    } else {
      addParamForm.value_type_sub = '';
      addParamForm.value_allowed = '';
    }
  };

  // 约束类型变更：切换到不需要允许值的类型时清空允许值
  const handleValueTypeSubChange = (value: string) => {
    if (NO_VALUE_ALLOWED_TYPES.includes(value) && addParamForm.value_allowed) {
      addParamForm.value_allowed = '';
    }
  };

  // 业务配置规则 Checkbox 变更
  const handleBizRuleCheckboxChange = (values: string[]) => {
    bizRuleCheckboxKeys.forEach((key) => {
      addParamForm[key] = values.includes(key) as never;
    });
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
        conf_file: props.version,
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
        conf_type: props.confType,
        meta_cluster_type: props.clusterType,
      });
      isShowAddParam.value = false;
      messageSuccess(isEditMode.value ? t('编辑成功') : t('新增成功'));
      isEditMode.value = false;
      emit('success');
    } finally {
      submitLoading.value = false;
    }
  };

  /** 打开新建模式 */
  const openCreate = () => {
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
    isAddParamFormDirty.value = false;
    isShowAddParam.value = true;
  };

  /** 打开编辑模式 */
  interface EditRowData {
    conf_name: string;
    conf_name_lc?: string | null;
    description?: string;
    flag_encrypt?: number;
    flag_readonly?: number;
    flag_visible?: number;
    need_restart?: number;
    value_allowed?: string | null;
    value_default?: string | null;
    value_type?: string | null;
    value_type_sub?: string | null;
  }

  const openEdit = (row: EditRowData) => {
    isEditMode.value = true;
    Object.assign(addParamForm, {
      conf_name: row.conf_name,
      conf_name_lc: row.conf_name_lc ?? '',
      description: row.description,
      flag_empty_string:
        !row.value_default && row.value_type === 'STRING' && (!row.value_type_sub || row.value_type_sub === 'STRING'),
      flag_encrypt: row.flag_encrypt === 1,
      flag_readonly_inverse: row.flag_readonly === 0,
      flag_visible: row.flag_visible === 1,
      need_restart: row.need_restart === 1,
      value_allowed: row.value_allowed ?? '',
      value_default: row.value_default ?? '',
      value_type: row.value_type ?? '',
      value_type_sub: row.value_type === 'STRING' && row.value_type_sub === '' ? NO_CONSTRAINT : row.value_type_sub,
    });
    isAddParamFormDirty.value = false;
    isShowAddParam.value = true;
  };

  defineExpose({ openCreate, openEdit });
</script>

<style lang="less" scoped>
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

      .bk-form-item {
        flex: 1;
      }
    }

    .form-item-tips {
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      position: absolute;
    }

    .default-value-row {
      display: flex;
      align-items: center;

      .empty-string-checkbox {
        white-space: nowrap;
        flex-shrink: 0;
      }
    }

    .bk-checkbox-group {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .bk-checkbox ~ .bk-checkbox {
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
</style>
