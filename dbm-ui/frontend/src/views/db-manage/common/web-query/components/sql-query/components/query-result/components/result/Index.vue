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
  <div
    ref="resultMainRef"
    class="panel-results-main">
    <div class="results-info-main">
      <div class="counts-display">
        <span>{{ t('查询结果') }}</span>
        <span class="ml-4 mr-4">:</span>
        <I18nT
          keypath="共m条"
          tag="span">
          <span style="font-weight: 700; color: #63656e">{{ tableData.length }}</span>
        </I18nT>
        <span class="ml-4 mr-4">,</span>
        <span>{{ t('耗时') }}</span>
        <span>{{ querySeconds }}s</span>
        <span class="ml-4 mr-4">,</span>
        <I18nT
          keypath="查询成功n个实例"
          tag="span">
          <span style="font-weight: 700; color: #2caf5e">{{ successInstances }}</span>
        </I18nT>
        <template v-if="failedInstances.length">
          <span class="ml-4 mr-4">,</span>
          <I18nT
            keypath="查询失败n个实例"
            tag="span">
            <span style="font-weight: 700; color: #ea3636">{{ failedInstances.length }}</span>
          </I18nT>
          <span class="ml-4 mr-4">:</span>
          <div class="fail-list-main">
            <TextOverflowLayout>
              <span>{{ failedInstances.join(' , ') }}</span>
              <template #append>
                <DbIcon
                  v-bk-tooltips="t('复制失败实例')"
                  class="copy-icon"
                  type="copy"
                  @click="() => execCopy(failedInstances.join('\n'))" />
              </template>
            </TextOverflowLayout>
          </div>
        </template>
      </div>
      <BkButton
        text
        theme="primary"
        @click="handleExport">
        {{ t('导出结果') }}
      </BkButton>
    </div>
    <BkTable
      ref="tableRef"
      border="none"
      class="query-result-table"
      :class="{ 'is-no-table-data': !tableData.length }"
      :columns="columns"
      :data="tableData"
      :pagination="pagination"
      :pagination-limit="20"
      :remote-pagination="false"
      :row-config="{
        isHover: false,
        height: 28,
      }"
      stripe
      @page-limit-change="handlePageLimitChange"
      @page-value-change="handlePageValueChange" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, exportExcelFile, random } from '@utils';

  import type { DbConsoleResults } from '../../../../Index.vue';

  interface Props {
    data?: DbConsoleResults;
    dbType?: DBTypes;
    querySeconds?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    dbType: DBTypes.MYSQL,
    querySeconds: 0,
  });

  const { t } = useI18n();

  // 以防跟元数据中的key发生冲突
  const instanceId = random();

  const pagination = reactive({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 20,
    limitList: [10, 20, 50, 100],
  });
  const resultMainRef = ref<HTMLElement>();
  const columns = ref<
    {
      field: string;
      fixed?: string;
      label: string;
      width?: number;
    }[]
  >([]);

  const failedInstances = computed(() => {
    if (!props.data.length) {
      return [];
    }

    return props.data.filter((item) => !!item.error_msg).map((info) => info.instance);
  });

  const successInstances = computed(() => props.data.length - failedInstances.value.length);

  const tableData = computed(() => {
    if (!props.data.length) {
      return [];
    }

    return props.data.reduce<Record<string, string | number>[]>((list, item) => {
      if (!item.table_data) {
        return list;
      }

      item.table_data.forEach((row) => {
        list.push({
          [instanceId]: item.instance,
          ...row,
        });
      });
      return list;
    }, []);
  });

  watch(
    () => props.data,
    () => {
      if (props.data.length) {
        const firstValidTableData = props.data.find((item) => !!item.table_data);
        if (firstValidTableData) {
          const dataKeys = Object.keys(firstValidTableData.table_data[0]).map((key) => ({
            field: key,
            label: key,
          }));
          columns.value = [
            {
              field: instanceId,
              fixed: 'left',
              label: 'Instance',
              width: 200,
            },
            ...dataKeys,
          ];
        }
      } else {
        columns.value = [];
      }
    },
    { immediate: true },
  );

  watch(
    tableData,
    () => {
      pagination.count = tableData.value.length;
      if (tableData.value.length) {
        setTimeout(() => {
          resultMainRef.value?.scrollIntoView();
        });
      }
    },
    { immediate: true },
  );

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit) {
      return;
    }
    pagination.limit = pageLimit;
    pagination.current = 1;
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    if (pagination.current === pageValue) {
      return;
    }
    pagination.current = pageValue;
  };

  const handleExport = () => {
    const formatData = tableData.value.map((item) =>
      columns.value.reduce<Record<string, string>>((results, column) => {
        Object.assign(results, { [column.label]: item[column.field] });
        return results;
      }, {}),
    );
    const colsWidths = columns.value.map(() => ({ width: 30 }));

    exportExcelFile(formatData, colsWidths, 'Sheet1', `${props.dbType}_${t('管理控制台')}.xlsx`);
  };
</script>
<style lang="less" scoped>
  .panel-results-main {
    display: flex;
    flex-direction: column;

    .results-info-main {
      display: flex;
      height: 48px;
      padding: 0 16px;
      font-size: 12px;
      background: #fff;
      justify-content: space-between;
      align-items: center;

      .counts-display {
        flex: 1;
        display: flex;

        .fail-list-main {
          margin-right: 20px;
          overflow: hidden;
          flex: 1;

          .copy-icon {
            margin-left: 6px;
            font-size: 14px;
            color: #3a84ff;
            cursor: pointer;
          }
        }
      }
    }
  }
</style>
<style lang="less">
  .query-result-table {
    &.is-no-table-data {
      .vxe-table--header-wrapper {
        display: none;
      }
    }

    .vxe-table--header-inner-wrapper {
      height: 28px !important;
    }

    .vxe-header--column {
      padding: 3px 0 !important;
    }

    .vxe-table--append-wrapper {
      border-bottom: none;
    }
  }
</style>
