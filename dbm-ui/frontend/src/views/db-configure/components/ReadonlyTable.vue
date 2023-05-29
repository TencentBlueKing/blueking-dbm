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
  <div class="db-configure-readonly-parameters-table">
    <div class="mb-16">
      <BkInput
        v-model="search"
        clearable
        :placeholder="$t('请输入参数项')"
        style="width: 320px" />
    </div>
    <DbOriginalTable
      class="parameter-table"
      :columns="columns"
      :data="renderTableData"
      :is-anomalies="isAnomalies"
      :is-searching="!!search"
      :min-height="0"
      :show-overflow-tooltip="false"
      :style="{ '--sticky-top': `${stickyTop}px` }"
      @clear-search="handleClearSearch"
      @refresh="handleRefresh" />
  </div>
</template>
<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/source/configs';

  import {
    confLevelInfos,
    ConfLevels,
    type ConfLevelValues,
  } from '@common/const';

  import type { TableColumnRender } from '@/types/bkui-vue';

  type ParameterConfigItem = ServiceReturnType<typeof getLevelConfig>['conf_items'][number]

  interface Props {
    data?: ParameterConfigItem[]
    level?: string,
    // 是否为发布记录
    isRecord?: boolean,
    stickyTop?: number,
    isAnomalies?: boolean
  }

  interface Emits {
    (e: 'refresh'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    level: ConfLevels.PLAT,
    // 是否为发布记录
    isRecord: false,
    stickyTop: 0,
    isAnomalies: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const isPlat = computed(() => props.level === ConfLevels.PLAT);
  const search = ref('');
  const renderTableData = computed(() => {
    if (search.value === '') return props.data;
    return props.data.filter(item => item.conf_name.includes(search.value));
  });

  const columns: Column[] = [
    {
      label: t('参数项'),
      field: 'conf_name',
      render: ({ data }: TableColumnRender) => (
          <>
            <div
              v-overflow-tips
              class="text-overflow config-name-box">
              {data.conf_name}
            </div>
            <db-icon
              v-show={Boolean(data.description)}
              v-bk-tooltips={data.description}
              class="ml-4"
              type="attention" />
          </>
        ),
    },
    {
      label: t('参数值'),
      field: isPlat.value && !props.isRecord ? 'value_default' : 'conf_value',
      render: ({ cell }: TableColumnRender) => <div class="text-overflow" v-overflow-tips>{cell}</div>,
    },
    {
      label: t('允许值设定'),
      field: 'value_allowed',
      render: ({ cell, data }: TableColumnRender) => {
        const enumType = ['ENUM', 'ENUMS'];
        // 将 | 转为逗号(,) 增加可读性
        const displayValue = enumType.includes(data.value_type_sub as string) ? cell.replace(/\|/g, ', ') : cell;
        return <div class="text-overflow" v-overflow-tips>{displayValue}</div>;
      },
    },
    {
      label: t('锁定'),
      field: 'flag_locked',
      width: 130,
      render: ({ cell, data }: { cell: number, data: ParameterConfigItem }) => {
        if (cell === 0) {
          return (
            <db-icon type="unlock" />
          );
        }

        const text = isPlat.value ? t('平台锁定') : confLevelInfos[data.level_name as ConfLevelValues]?.lockText;
        return (
          <bk-tag class={['locked-tag', `locked-tag--${data.level_name}`]}>
            {{
              default: () => text,
              icon: () => <db-icon type="lock-fill" />,
            }}
          </bk-tag>
        );
      },
    },
    {
      label: t('重启实例生效'),
      field: 'need_restart',
      width: 200,
      render: ({ cell }: {cell: number}) => (cell === 1 ? t('是') : t('否')),
    },
  ];

  const handleClearSearch = () => {
    search.value = '';
  };
  const handleRefresh = () => {
    emits('refresh');
  };
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .db-configure-readonly-parameters-table {
    width: 100%;

    .config-name-box {
      display: inline-block;
      max-width: calc(100% - 18px);
      vertical-align: middle;
    }

    .parameter-table {
      .bk-table-body {
        height: calc(var(--height) - 42px) !important;
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
  }
</style>
