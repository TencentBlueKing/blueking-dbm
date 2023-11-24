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
  <DbForm
    ref="parameterFormRef"
    :model="data">
    <DbOriginalTable
      ref="parameterTableRef"
      class="parameter-table custom-edit-table"
      :columns="columns"
      :data="data"
      :is-anomalies="isAnomalies"
      :min-height="0"
      :row-class="setRowClass"
      :style="{ '--sticky-top': `${stickyTop}px` }"
      @refresh="handleRefresh" />
  </DbForm>
</template>
<script lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  // import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/source/configs';

  import {
    confLevelInfos,
    ConfLevels,
    type ConfLevelValues,
  } from '@common/const';

  import RangeInput from './RangeInput.vue';

  type ParameterConfigItem = ServiceReturnType<typeof getLevelConfig>['conf_items'][number]

  type TableColumn = {
    cell: string,
    data: ParameterConfigItem,
    index: number
  }

  export default {
    name: 'ParameterTable',
  };
</script>

<script setup lang="tsx">

  interface Props {
    parameters?: ParameterConfigItem[]
    data?: ParameterConfigItem[]
    // 没有任何变更的数据
    originData?: ParameterConfigItem[],
    level?: ConfLevelValues
    stickyTop?: number,
    isAnomalies?: boolean
  }

  interface Emits {
    (e: 'refresh'): void
    (e: 'addItem', index: number): void
    (e: 'removeItem', index: number): void
    (e: 'onChangeParameterItem', index: number, selected: ParameterConfigItem): void
    (e: 'onChangeEnums', index: number, value: string[]): void
    (e: 'onChangeMultipleEnums', index: number, key: string, value: string[]): void
    (e: 'onChangeRange', index: number,  range: { max: number, min: number }): void
    (e: 'onChangeNumberInput', index: number,  key: 'value_default' | 'conf_value', value: number): void // ChangeLock(index: number, value: boolean)
    (e: 'onChangeLock', index: number, value: boolean): void
  }

  const props = withDefaults(defineProps<Props>(), {
    parameters: () => [],
    data: () => [],
    originData: () => [],
    level: ConfLevels.PLAT,
    stickyTop: 0,
    isAnomalies: false,
  });

  // eslint-disable-next-line func-call-spacing
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const isPlat = computed(() => props.level === ConfLevels.PLAT);
  // 参数项映射
  const parameterMap = computed<any>(() => (
    props.originData.reduce((map: any, item) => Object.assign(map, { [item.conf_name]: item }), {})
  ));

  // 锁定提示变量
  const tipsAgain = ref(true); // 是否再一次显示
  const controlShow = ref(false); // 控制显示隐藏
  const needShow = computed(() => controlShow.value && tipsAgain.value); // 是否显示
  // 配合 controlShow 控制当前行显示隐藏
  const lockTipsList = computed(() => Array.from({ length: props.data.length }, () => false));

  const columns: Column[] = [{
    label: t('参数项'),
    field: 'conf_name',
    showOverflowTooltip: false,
    render: ({ cell, data, index }: TableColumn) => {
      if (data.op_type === 'add') {
        return (
          <bk-select
            model-value={cell}
            filterable
            popover-min-width={420}
            clearable={false}
            onChange={handleSelected.bind(this, index)}>
            {
              getSelectableParameters(data).map((item: ParameterConfigItem) => (
                <bk-option value={item.conf_name} label={item.conf_name} />
              ))
            }
          </bk-select>
        );
      }
      return <div class="text-overflow pl-10 pr-10" v-overflow-tips>{cell}</div>;
    },
  }, {
    label: t('参数值'),
    field: isPlat.value ? 'value_default' : 'conf_value',
    showOverflowTooltip: false,
    render: ({ cell, data, index }: TableColumn) => {
      // 被上层配置锁定无法编辑
      if (!isPlat.value && props.level !== data.level_name && data.flag_locked === 1) {
        return <div class="text-overflow pl-10 pr-10" v-overflow-tips>{cell}</div>;
      }

      const key = isPlat.value ? 'value_default' : 'conf_value';
      const property = data.value_allowed === '' ? '' : `${index}.${key}`;

      if (data.value_type_sub === 'ENUM') {
        if (data.value_allowed === '') return <bk-input v-model={props.data[index][key]} />;

        const tags = data.value_allowed.split('|').map(value => value.trim());
        // 确保参数值在枚举范围内
        // if (!tags.includes(cell)) {
        //   const [id] = tags;
        //   props.data[index][key] = id;
        // }
        const rules = [{
          trigger: 'blur',
          message: t('请输入允许值范围内的值'),
          validator: (validateValue: string) => tags.includes(validateValue),
        }];
        return (
          <bk-form-item key={index} label-width="0" rules={rules} property={property} error-display-type="tooltips">
            <bk-select v-model={props.data[index][key]} filterable clearable={false}>
              {
                tags.map((id: string) => <bk-option label={id} value={id} />)
              }
            </bk-select>
          </bk-form-item>
        );
      }

      if (data.value_type_sub === 'ENUMS') {
        if (data.value_allowed === '') return <bk-input v-model={props.data[index][key]} />;

        const tags = data.value_allowed.split('|').map(value => value.trim());
        // const isEvery = (values: string[]) => values.every(item => tags.includes(item));
        // 确保参数值在枚举范围内
        // if (!isEvery(cell.split(','))) {
        //   const [id] = tags;
        //   props.data[index][key] = id;
        // }
        const rules = [{
          trigger: 'blur',
          message: t('请输入允许值范围内的值'),
          validator: (validateValue: string) => {
            const values = validateValue.split(',');
            return values.every(item => tags.includes(item));
          },
        }];
        const modelValue = (props.data[index][key] as string).split(',');
        return (
          <bk-form-item key={index} label-width="0" rules={rules} property={property} error-display-type="tooltips">
            <bk-select
              model-value={modelValue}
              clearable={false}
              multiple
              filterable
              onChange={handleChangeMultipleEnums.bind(null, index, key)}>
              {
                tags.map((id: string) => <bk-option label={id} value={id} />)
              }
            </bk-select>
          </bk-form-item>
        );
      }

      if (data.value_type_sub === 'RANGE') {
        const values = data.value_allowed.match(/[-]?\d+/g);
        if (values === null) return (
          <bk-input model-value={props.data[index][key]} type="number" onChange={handleChangeNumberInput.bind(this, index, key)} />
        );

        const [min, max] = values;
        const rules = [{
          trigger: 'blur',
          message: t('请输入允许值范围内的值'),
          validator: (validateValue: string) => {
            if (validateValue === '') return false;

            const toNumberValue = Number(validateValue);
            return (
              Number.isFinite(toNumberValue)
              && toNumberValue <= Number(max)
              && toNumberValue >= Number(min)
            );
          },
        }];
        return (
          <bk-form-item key={index} label-width="0" rules={rules} property={property} error-display-type="tooltips">
            <bk-input model-value={props.data[index][key]} type="number"  onChange={handleChangeNumberInput.bind(this, index, key)} />
          </bk-form-item>
        );
      }

      return <bk-input v-model={props.data[index][key]} />;
    },
  }, {
    label: () => (
      <span
        class="table-header-custom"
        v-bk-tooltips={{
          content: t('参数值的可填写的范围'),
          theme: 'light',
        }}>
        {t('允许值设定')}
      </span>
    ),
    field: 'value_allowed',
    showOverflowTooltip: false,
    render: ({ cell, data, index }: TableColumn) => {
      const enumType = ['ENUM', 'ENUMS'];
      if (isPlat.value === false) {
        // 将 | 转为逗号(,) 增加可读性
        const displayValue = enumType.includes(data.value_type_sub as string) ? cell.replace(/\|/g, ', ') : cell;
        return <div class="text-overflow" v-overflow-tips>{displayValue}</div>;
      }

      if (enumType.includes(data.value_type_sub as string)) {
        const tags = cell === '' ? [] : cell.split('|').map(value => value.trim());
        return (
          <bk-tag-input
            key={index}
            model-value={tags}
            list={[]}
            clearable={false}
            placeholder={t('请输入枚举值Enter结束')}
            allow-create
            has-delete-icon
            onChange={handleChangeEnums.bind(this, index)} />
        );
      }
      if (data.value_type_sub === 'RANGE') {
        const [min, max] = cell.match(/[-]?\d+/g) || [0, 0];
        return (
          <RangeInput
            key={index}
            min={Number(min)}
            max={Number(max)}
            onChange={handleChangeRange.bind(this, index)} />
        );
      }
      return <bk-input v-model={props.data[index].value_allowed} key={index} />;
    },
  }, {
    label: () => {
      const isApp = props.level === ConfLevels.APP;
      const isModuel = props.level === ConfLevels.MODULE;
      return (
        <bk-popover
          width={270}
          theme="light"
          placement="top"
          boundary={document.body}
          fixOnBoundary={true}>
          {{
            default: () => <span class="table-header-custom">{t('锁定')}</span>,
            content: () => (
              <span>
                {t('如勾选_在配置发布后_新增实例将自动使用该配置_存量实例不受影响_且在')}
                {
                  isPlat.value ? <span><a href="javascript:">{t('业务配置')}</a>，</span> : null
                }
                {
                  isPlat.value || isApp ? <span><a href="javascript:">{t('模块配置')}</a>，</span> : null
                }
                {
                  isPlat.value || isApp || isModuel ? <span><a href="javascript:">{t('集群配置')}</a></span> : null
                }
                {t('中不可修改')}
              </span>
            ),
          }}
        </bk-popover>
      );
    },
    field: 'flag_locked',
    width: 140,
    render: ({ cell, data, index }: Omit<TableColumn, 'cell'> & { cell: number }) => {
      const { level_name: levelName } = data;
      // 集群没有锁定功能
      if (props.level === ConfLevels.CLUSTER && cell === 0) {
        return <i class="db-icon-unlock" />;
      }

      // 被上层配置锁定
      if (!isPlat.value && props.level !== levelName && cell === 1) {
        return (
          <bk-tag class={['locked-tag', `locked-tag--${levelName}`]}>
            {{
              default: () => confLevelInfos[levelName as ConfLevelValues]?.lockText,
              icon: () => <i class="db-icon-lock-fill" />,
            }}
          </bk-tag>
        );
      }

      const isShow = props.data[index].flag_locked === 1 && lockTipsList.value[index] && needShow.value;
      return (
        <bk-popover
          isShow={isShow}
          key={index}
          width={270}
          theme="light"
          placement="right"
          trigger="manual"
          boundary={document.body}
          fixOnBoundary={true}>
          {{
            default: () => (
              <bk-checkbox
                model-value={props.data[index].flag_locked === 1}
                onChange={handleChangeLock.bind(this, index)} />
            ),
            content: () => (
              <div class="lock-tips">
                <strong>{t('锁定提醒')}</strong>
                <p>{t('锁定后_已经运行的集群不受影响_新增的集群实例将自动使用该配置_且不能修改')}</p>
                <div class="buttons">
                  <bk-button size="small" theme="primary" onClick={hanldeCloseLockTips}>{t('知道了')}</bk-button>
                </div>
              </div>
            ),
          }}
        </bk-popover>
      );
    },
  }, {
    label: t('描述'),
    field: 'description',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string }) => <div class="text-overflow" v-overflow-tips>{cell}</div>,
  }, {
    label: t('重启实例生效'),
    field: 'need_restart',
    width: 200,
    render: ({ cell }: { cell: number }) => (cell === 1 ? <span style="color: #ff9c01;">{t('是')}</span> : t('否')),
  }, {
    label: () => (
      <bk-popover
        theme="light"
        placement="top"
        boundary={document.body}
        fixOnBoundary={true}>
        {{
          default: () => <span class="table-header-custom">{t('操作')}</span>,
          content: () => (
            <span style="color: #63656e;">
              <p>+ {t('增加1个当前层级关注的参数项')}</p>
              <p>— {t('即解除纳管_表示不再关心该参数值')}</p>
            </span>
          ),
        }}
      </bk-popover>
    ),
    field: 'operation',
    width: 120,
    render: ({ index, data }: TableColumn) => {
      // 被上层配置锁定无法删除
      const isPrevLevelLocked = !isPlat.value && props.level !== data.level_name && data.flag_locked === 1;
      return (
        <div class="operation">
          {
            props.data.length >= props.parameters.length
              ? null
              : (
                <bk-button
                  class="operation__icon mr-12"
                  text
                  onClick={handleAdd.bind(this, index)}>
                  <i class="db-icon-plus-fill" />
                </bk-button>
              )
          }
          {
            props.data.length > 1 && !isPrevLevelLocked
              ? (
                <bk-button
                  class="operation__icon"
                  text
                  onClick={handleRemove.bind(this, index)}>
                  <i class="db-icon-minus-fill" />
                </bk-button>
              )
              : null
          }
        </div>
      );
    },
  }];

  /**
   * 不再显示
   */
  function hanldeCloseLockTips()  {
    tipsAgain.value = false;
  }

  /**
   * 获取参数项可选列表
   */
  function getSelectableParameters(data: ParameterConfigItem) {
    const selected = props.data
      .filter((item: ParameterConfigItem) => item.conf_name !== data.conf_name)
      .map((item: ParameterConfigItem) => item.conf_name);
    return props.parameters.filter((item: ParameterConfigItem) => !selected.includes(item.conf_name));
  }

  /**
   * 选择参数项
   */
  function handleSelected(index: number, value: string) {
    const selected = props.parameters.find(item => item.conf_name === value);
    if (selected) {
      emits('onChangeParameterItem', index, selected);
    }
  }

  /**
   * enums change
   */
  function handleChangeEnums(index: number, value: string[]) {
    emits('onChangeEnums', index, value);
    // props.data[index].value_allowed = value.join('|');
  }

  /**
   * enums multiple change
   */
  function handleChangeMultipleEnums(index: number, key: string, value: string[]) {
    emits('onChangeMultipleEnums', index, key, value);
  }

  /**
   * range change
   */
  function handleChangeRange(index: number, { min, max }: { max: number, min: number }) {
    emits('onChangeRange', index, { max, min });
    // props.data[index].value_allowed = (min || max) ? `[${min || 0},${max || 0}]` : '';
  }

  // 用于记录锁定前层级信息
  // const lockLevelNameMap: Record<string, string | undefined> = {};

  /**
   * lock change
   */
  function handleChangeLock(index: number, value: boolean) {
    emits('onChangeLock', index, value);
    // 设置 tips 信息
    if (tipsAgain) {
      lockTipsList.value.forEach((_, index) => {
        lockTipsList.value[index] = false;
      });
    }

    lockTipsList.value[index] = value;
    controlShow.value = true;

    // const lockedValue = Number(value);
    // const isLocked = lockedValue === 1;
    // const data = props.data[index];
    // props.data[index].flag_locked = lockedValue;

    // if (isPlat.value === false) {
    //   // 锁定前记录层级信息
    //   if (isLocked) {
    //     lockLevelNameMap[data.conf_name] = data.level_name;
    //   }
    //   // 锁定则将层级信息设置为当前层级，反之则恢复层级信息
    //   props.data[index].level_name = isLocked ? props.level : lockLevelNameMap[data.conf_name];
    // }
  }

  /**
   * 将 number input 的值调整为 string 类型，否则 diff 会出现类型不一样
   */
  function handleChangeNumberInput(index: number, key: 'value_default' | 'conf_value', value: number) {
    emits('onChangeNumberInput', index, key, value);
    // props.data[index][key] = String(value);
  }

  /**
   * 设置行样式
   */
  function setRowClass(row: ParameterConfigItem, index: number) {
    const origin = parameterMap.value[row.conf_name];
    if (row.op_type === 'add' && !origin) {
      return 'parameter-add';
    }
    // row 会带有表格内置属性，所以用index取
    return JSON.stringify(origin) !== JSON.stringify(props.data[index]) ? 'parameter-update' : '';
  }

  /**
   * 添加参数配置
   */
  const parameterTableRef = ref();
  function handleAdd(index: number) {
    emits('addItem', index);
    // props.data.splice(index + 1, 0, {
    //   conf_name: '',
    //   conf_name_lc: '',
    //   description: '',
    //   flag_disable: 0,
    //   flag_locked: 0,
    //   need_restart: 0,
    //   value_allowed: '',
    //   value_default: '',
    //   value_type: '',
    //   value_type_sub: '',
    //   op_type: 'add',
    // });

    setTimeout(() => {
      // 滑动到添加的行
      const table = parameterTableRef.value.$el as HTMLElement;
      if (table) {
        const [tableBody] = Array.from(table.getElementsByClassName('bk-table-body'));
        if (tableBody) {
          const item = tableBody.getElementsByTagName('tr')[index + 1] as HTMLElement;
          if (item) {
            const { scrollTop, clientHeight } = tableBody;

            if (item.offsetTop - scrollTop > clientHeight) {
              tableBody.scrollTo({
                top: scrollTop + 64,
              });
            }
          }
        }
      }
    });
  }

  /**
   * remove row
   */
  function handleRemove(index: number) {
    parameterFormRef.value.clearValidate();
    emits('removeItem', index);
    // props.data.splice(index, 1);
  }

  function handleRefresh() {
    emits('refresh');
  }

  /**
   * 校验参数配置
   */
  const parameterFormRef = ref();
  const validate = () => parameterFormRef.value?.validate()
    .then(() => Promise.resolve(true))
    .catch((res: any) => {
      // 定位到报错列表
      const form = parameterFormRef.value.$el as HTMLElement;
      const [firstErrorElement] = Array.from(form.getElementsByClassName('bk-form-item is-error'));
      firstErrorElement?.scrollIntoView({ block: 'center' });
      return Promise.reject(res);
    });

  defineExpose({ validate });
</script>

<style lang="less">
  @import "@styles/mixins.less";

  .parameter-table.custom-edit-table {
    .sticky-table(var(--sticky-top));

    .bk-table-body {
      height: calc(var(--height) - 42px) !important;

      .bk-table-body-content {
        .parameter-add {
          td {
            background: #f1fcf5 !important;
          }

          &:not(:hover) {
            .bk-input--text,
            .bk-tag-input .bk-tag-input-trigger,
            .bk-tag-input .bk-tag-input-trigger .tag-input,
            .bk-select-input,
            .range-input {
              background-color: #f1fcf5;
            }
          }
        }

        .parameter-update {
          td {
            background: #fff8e7 !important;
          }

          &:not(:hover) {
            .bk-input--text,
            .bk-tag-input .bk-tag-input-trigger,
            .bk-tag-input .bk-tag-input-trigger .tag-input,
            .bk-select-input,
            .range-input {
              background-color: #fff8e7;
            }
          }
        }
      }
    }

    .table-header-custom {
      line-height: 20px;
      border-bottom: 1px dashed @light-gray;
    }

    .bk-tag-input {
      display: inline-block;
      width: 100%;
      margin: 4px 0;
      vertical-align: middle;

      .tag-list {
        max-height: 96px !important;
      }
    }

    .bk-input--number-control {
      display: none;
    }

    .bk-form-item {
      display: inline-block;
      width: 100%;
      vertical-align: middle;

      .bk-form-label {
        display: none;
      }
    }

    .bk-checkbox {
      vertical-align: sub;
    }

    .operation {
      &__icon {
        font-size: @font-size-large;
        color: @light-gray;

        &:hover {
          color: @default-color;
        }

        &.is-disabled {
          color: @disable-color;
        }
      }
    }

    .locked-tag {
      &--app {
        color: @primary-color;
        background-color: rgb(58 132 255 / 10%);
        border-color: rgb(58 132 255 / 30%);
      }

      &--module {
        color: #1983c0;
        background-color: rgb(195 233 255 / 60%);
        border-color: rgb(195 233 255 / 60%);
      }
    }
  }

  .lock-tips {
    strong {
      color: @title-color;
    }

    p {
      padding: 6px 0 12px;
      color: @default-color;
    }

    .buttons {
      text-align: right;

      .bk-button-small {
        display: inline-block;
        height: unset;
        padding: 0 4px;
        margin-left: 16px;
        font-size: @font-size-mini;
        line-height: 18px;
      }
    }
  }
</style>
