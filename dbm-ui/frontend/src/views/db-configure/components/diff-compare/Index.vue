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
  <div class="diff-compare">
    <ValueDiff
      :count="diff.count"
      :data="diff.data"
      :labels="labels" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/source/configs';

  import { ConfLevels, type ConfLevelValues } from '@common/const';

  import { useDiff } from '@views/db-configure/hooks/useDiff';

  import ValueDiff from './components/ValueDiff.vue';

  interface Props {
    data?: ServiceReturnType<typeof getLevelConfig>['conf_items'];
    level?: ConfLevelValues;
    origin?: ServiceReturnType<typeof getLevelConfig>['conf_items'];
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    level: ConfLevels.PLAT,
    origin: () => [],
  });

  const { t } = useI18n();
  const diffData = computed(() => props.data);
  const diffOrigin = computed(() => props.origin);
  const valueKey = computed(() => (props.level === ConfLevels.PLAT ? 'value_default' : 'conf_value'));
  const diff = useDiff(diffData, diffOrigin);

  const getUnmanagedNode = () => (
    <span
      v-bk-tooltips={t('解除纳管表示不再关心该配置项的值')}
      class='diff-compare__unmanaged'>
      {t('解除纳管')}
    </span>
  );

  const labels = [
    {
      key: valueKey.value,
      label: `${t('参数值')}:`,
      render: (row: any, columnKey: string) => {
        if (row.status === 'create' && columnKey === 'before') {
          return '--';
        }

        if (row.status === 'delete' && columnKey === 'after') {
          return getUnmanagedNode();
        }

        return row[columnKey][valueKey.value];
      },
    },
    {
      key: 'value_allowed',
      label: `${t('允许值范围')}: `,
      render: (row: any, columnKey: string) => {
        if (row.status === 'create' && columnKey === 'before') {
          return '--';
        }

        if (row.status === 'delete' && columnKey === 'after') {
          return getUnmanagedNode();
        }

        const value = row[columnKey].value_allowed;

        if (!value) return '--';

        if (row[columnKey].value_type_sub === 'RANGE') {
          const [min, max] = value.match(/\d+/g);
          return `${min}～${max}`;
        }

        // 将 | 转为逗号(,) 增加可读性
        if (['ENUM', 'ENUMS'].includes(row[columnKey].value_type_sub as string)) {
          return (
            <div
              v-overflow-tips
              class='text-overflow'>
              {value.replace(/\|/g, ', ')}
            </div>
          );
        }

        return value;
      },
      showOverflowTooltip: false,
    },
    {
      key: 'flag_locked',
      label: `${t('是否锁定')}: `,
      render: (row: any, columnKey: string) => {
        if (row.status === 'create' && columnKey === 'before') {
          return '--';
        }

        if (row.status === 'delete' && columnKey === 'after') {
          return getUnmanagedNode();
        }

        return <i class={row[columnKey].flag_locked === 0 ? 'db-icon-unlock' : 'db-icon-lock-fill'} />;
      },
    },
  ];
</script>

<style lang="less">
  .diff-compare {
    &__unmanaged {
      border-bottom: 1px dashed @border-danger;
    }
  }
</style>
