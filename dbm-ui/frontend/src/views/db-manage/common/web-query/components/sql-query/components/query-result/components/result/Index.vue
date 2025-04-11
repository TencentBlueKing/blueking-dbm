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
  <div class="panel-results-main">
    <div class="results-info-main">
      <div class="counts-display">
        <span>{{ t('查询结果') }}</span>
        <span class="ml-4 mr-4">:</span>
        <I18nT
          keypath="共m条"
          tag="span">
          <span style="font-weight: 700; color: #63656e">{{ queryResults.length }}</span>
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
    <DbTable
      ref="tableRef"
      border="none"
      class="query-result-table"
      :columns="columns"
      :container-height="containerHeight"
      :data-source="dataSource"
      :pagination-limit="20"
      :remote-pagination="false"
      :row-config="{
        isHover: false,
        height: 28,
      }"
      stripe
      @pagination-change="handlePaginationChange" />
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

  const tableRef = ref();
  const containerHeight = ref(800);
  const columns = ref<
    {
      field: string;
      fixed?: string;
      label: string;
      width?: number;
    }[]
  >([]);

  const failedInstances = computed(() => {
    if (!props.data.length || !props.data[0].table_data) {
      return [];
    }

    return props.data.filter((item) => !!item.error_msg).map((info) => info.instance);
  });

  const successInstances = computed(() => props.data.length - failedInstances.value.length);

  const queryResults = computed(() => {
    if (!props.data.length || !props.data[0].table_data) {
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

  const dataSource = computed(() => {
    if (!props.data.length || !columns.value.length || !queryResults.value.length) {
      return () =>
        Promise.resolve({
          count: 0,
          results: [],
        });
    }

    return () =>
      Promise.resolve({
        count: queryResults.value.length,
        results: queryResults.value,
      });
  });

  watch(
    () => props.data,
    () => {
      if (props.data.length && props.data[0].table_data) {
        const dataKeys = Object.keys(props.data[0].table_data[0]).map((key) => ({
          field: key,
          label: key,
        }));
        columns.value = [
          {
            field: instanceId,
            fixed: 'left',
            label: 'Instance',
            width: 160,
          },
          ...dataKeys,
        ];
      } else {
        columns.value = [];
      }
    },
    { immediate: true },
  );

  watch(
    dataSource,
    () => {
      setTimeout(() => {
        tableRef.value?.fetchData();
      });
    },
    {
      immediate: true,
    },
  );

  const handlePaginationChange = (data: { limit: number }) => {
    if (data.limit > 20) {
      containerHeight.value = 800 + (data.limit - 20) * 28;
      return;
    }

    containerHeight.value = 800;
  };

  const handleExport = () => {
    const formatData = queryResults.value.map((item) =>
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
    .vxe-table--header-inner-wrapper {
      height: 28px !important;
    }

    .vxe-header--column {
      padding: 3px 0 !important;
    }
  }
</style>
