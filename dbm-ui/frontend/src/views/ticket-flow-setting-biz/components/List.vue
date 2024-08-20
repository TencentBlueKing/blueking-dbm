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
  <Teleport to="#dbContentTitleAppend">
    <BkTag
      class="ml-8"
      theme="info">
      {{ t('业务') }}
    </BkTag>
  </Teleport>
  <div class="ticket-flow-list-content">
    <div class="top-operation">
      <BkAlert
        class="alert-box"
        closable>
        {{ t('内置策略不支持更改。如需自定义配置，可通过追加配置来更改目标和是否审批') }}
      </BkAlert>
      <BkSearchSelect
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList"
        :placeholder="t('请选择条件搜索')"
        unique-select
        value-split-code="+"
        @search="fetchData" />
    </div>
    <div class="tickets-flow-table">
      <BkLoading :loading="loading">
        <BkTable
          :data="tableData"
          :pagination="pagination"
          remote-pagination
          @page-limit-change="handeChangeLimit"
          @page-value-change="handleChangePage">
          <BkTableColumn
            :label="t('单据类型')"
            :rowspan="rowSpan"
            :width="240">
            <template #default="{ data }">
              <TextOverflowLayout>
                {{ data.ticket_type_display }}
                <template #append>
                  <BkButton
                    class="append-config-btn"
                    size="small"
                    @click="(event: PointerEvent) => handleShowAppendConfig(data, event)">
                    {{ t('追加配置') }}
                  </BkButton>
                </template>
              </TextOverflowLayout>
            </template>
          </BkTableColumn>
          <BkTableColumn
            :label="t('目标')"
            :width="200">
            <template #default="{ data }">
              <RenderRow
                v-if="data.isCustomTarget"
                :data="data.clusterDomainList"
                show-all>
                <template #prepend>
                  <span class="mr-4">{{ t('集群') }} :</span>
                </template>
                <template #append>
                  <BkTag
                    class="ml-4"
                    size="small"
                    theme="success">
                    {{ t('自定义') }}
                  </BkTag>
                  <EditConfig
                    v-model:isShow="showEditConfig"
                    :data="data"
                    @success="fetchData">
                    <DbIcon
                      v-bk-tooltips="t('修改目标')"
                      class="is-custom ml-4"
                      type="bk-dbm-icon db-icon-edit"
                      @click="() => (showEditConfig = true)" />
                  </EditConfig>
                </template>
              </RenderRow>
              <TextOverflowLayout v-else-if="!data.hidden">
                {{ t('业务下全部对象') }}
                <template #append>
                  <BkTag
                    class="ml-4"
                    size="small">
                    {{ t('内置') }}
                  </BkTag>
                </template>
              </TextOverflowLayout>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="need_itsm"
            :label="renderHead('need_itsm')"
            :width="120">
            <template #default="{ data }">
              <RenderFlowPreview
                v-model="data.configs.need_itsm"
                config-key="need_itsm"
                :data="data"
                @success="fetchData">
                <AuthTemplate
                  action-id="ticket_config_set"
                  class="flow-node-action"
                  :permission="data.permission.ticket_config_set"
                  :resource="props.dbType">
                  <BkCheckbox
                    v-model:model-value="data.configs.need_itsm"
                    style="pointer-events: none" />
                </AuthTemplate>
              </RenderFlowPreview>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="need_manual_confirm"
            :label="renderHead('need_manual_confirm')"
            :width="120">
            <template #default="{ data }">
              <RenderFlowPreview
                v-model="data.configs.need_manual_confirm"
                config-key="need_manual_confirm"
                :data="data"
                @success="fetchData">
                <AuthTemplate
                  action-id="ticket_config_set"
                  class="flow-node-action"
                  :permission="data.permission.ticket_config_set"
                  :resource="props.dbType">
                  <BkCheckbox
                    v-model:model-value="data.configs.need_manual_confirm"
                    style="pointer-events: none" />
                </AuthTemplate>
              </RenderFlowPreview>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="flow_desc"
            :label="t('流程预览')"
            show-overflow-tooltip
            :width="400">
            <template #default="{ data }">
              <span>{{ data.flow_desc.join(' -> ') }}</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="updater"
            :label="t('更新人')"
            show-overflow-tooltip
            :width="120" />
          <BkTableColumn
            field="updateAtDisplay"
            :label="t('更新时间')"
            show-overflow-tooltip
            sort
            :width="240" />
          <BkTableColumn
            :label="t('操作')"
            :width="100">
            <template #default="{ data }">
              <BkButton
                v-bk-tooltips="{
                  content: t('内置目标不支持编辑'),
                  disabled: data.isCustomTarget,
                }"
                :disabled="!data.isCustomTarget"
                text
                theme="primary"
                @click="(event: PointerEvent) => handleShowAppendConfig(data, event, true)">
                {{ t('编辑') }}
              </BkButton>
              <DeleteConfig
                v-if="data.isCustomTarget"
                v-model="data.id"
                :data="data"
                @success="fetchData">
                <BkButton
                  class="is-custom ml-8"
                  text
                  theme="primary">
                  {{ t('删除') }}
                </BkButton>
              </DeleteConfig>
            </template>
          </BkTableColumn>
          <template #empty>
            <slot name="empty">
              <EmptyStatus
                :is-anomalies="isAnomalies"
                :is-searching="searchValue.length > 0"
                @clear-search="handleClearSearch"
                @refresh="fetchData" />
            </slot>
          </template>
        </BkTable>
      </BkLoading>
    </div>
  </div>
  <AppendConfigSide
    v-model:isShow="appendConfig.isShow"
    :data="appendConfig.data"
    @success="fetchData" />
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe'
  import {
    getTicketTypes,
    queryTicketFlowDescribe,
  } from '@services/source/ticket';

  import { useDefaultPagination } from '@hooks';

  import type { DBTypes } from '@common/const';

  import RenderRow from '@components/render-row/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import AppendConfigSide from './AppendConfigSide.vue';
  import DeleteConfig from "./DeleteConfig.vue";
  import EditConfig from './EditConfig.vue';
  import RenderFlowPreview from './RenderFlowPreview.vue';

  interface IDataRow extends TicketFlowDescribeModel {
    rowSpan: number;
  }

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const ticketTypeList = shallowRef<ISearchItem[]>([]);
  const searchValue = ref<Array<ISearchItem & { values: ISearchItem[] }>>([]);
  const showEditConfig = ref(false);
  const isAnomalies = ref(false);
  const pagination = ref(useDefaultPagination());
  const allTableData = shallowRef<IDataRow[]>([]);
  const appendConfig = reactive({
    isShow: false,
    data: {} as TicketFlowDescribeModel,
  });

  const reqParams = computed(() =>
    searchValue.value.reduce<Record<string, string>>((obj, item) => {
      Object.assign(obj, {
        [item.id]: item.values.map((data) => data.id).join(','),
      });
      return obj;
    }, {}),
  );
  const searchSelectList = computed(() => [
    {
      name: t('单据类型'),
      id: 'ticket_types',
      multiple: true,
      children: ticketTypeList.value,
    },
  ]);
  const tableData = computed(() => {
    const { current, limit } = pagination.value;
    // 计算起始索引
    const startIndex = (current - 1) * limit;
    // 计算结束索引
    const endIndex = startIndex + limit;
    return allTableData.value.slice(startIndex, endIndex);
  })

  useRequest(getTicketTypes, {
    onSuccess: (data) => {
      ticketTypeList.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  const {
    run: queryTicketFlowDescribeRun,
    loading,
  } = useRequest(queryTicketFlowDescribe, {
    manual: true,
    onSuccess(data) {
      pagination.value.count = data.count;
      const resultsMap = _.groupBy(data.results, 'ticket_type');
      allTableData.value = Object.values(resultsMap).flatMap(values => {
        let rowSpan = values.length;
        return values
          .map(item => ({
            ..._.cloneDeep(item),
            updateAtDisplay: item.updateAtDisplay,
            isCustomTarget: item.isCustomTarget,
            clusterDomainList: item.clusterDomainList,
            rowSpan,
          }))
          .filter(item => rowSpan === 1 || item.isCustomTarget ? true : (rowSpan -= 1, false));
      });
      isAnomalies.value = false;
    },
    onError() {
      pagination.value.count = 0;
      allTableData.value = [];
      isAnomalies.value = true;
    },
  });

  watch(reqParams, () => {
    fetchData();
  });

  watch(
    () => props.dbType,
    (type) => {
      if (type) {
        searchValue.value = [];
      }
    },
  );

  const handleClearSearch = () => {
    searchValue.value = [];
  };

  const renderHead = (key: 'need_itsm' | 'need_manual_confirm') => {
    if (key === 'need_itsm') {
      return (
        <p
          class="configs-head"
          v-bk-tooltips={t('是否经由DBA审批后才可执行')}>
          {t('是否审批')}
        </p>
      )
    }
    return (
      <p
        class="configs-head"
        v-bk-tooltips={t('是否经由提单人确认后才可执行')}>
        {t('是否人工确认')}
      </p>
    )
  }

  const rowSpan = ({ row }: {
    column: any;
    colIndex: number;
    row: IDataRow;
    rowIndex: number;
  }) => row.rowSpan;

  const fetchData = () => {
    queryTicketFlowDescribeRun({
      ...reqParams.value,
      db_type: props.dbType,
    });
  };

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    handleChangePage(1);
  };

  const handleShowAppendConfig = (data: IDataRow, e: PointerEvent, isEdit = false) => {
    e?.stopPropagation();
    const cloneData = _.cloneDeep(data);
    if (!isEdit) {
      appendConfig.data = Object.assign(cloneData, {
        bk_biz_id: 0,
        cluster_ids: [],
        configs: {
          need_itsm: false,
          need_manual_confirm: cloneData.configs.need_manual_confirm,
        },
      });
    } else {
      appendConfig.data = cloneData;
    }
    appendConfig.isShow = true;
  }

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less" scoped>
  .ticket-flow-list-content {
    display: flex;
    padding: 16px 24px;
    flex-direction: column;

    .top-operation {
      display: flex;
      width: 100%;
      height: 32px;
      justify-content: flex-end;
      margin-bottom: 16px;

      .alert-box {
        flex: 1;
        min-width: 490px;
        margin-right: 16px;
      }

      .input-box {
        width: 600px;
      }
    }

    .tickets-flow-table {
      :deep(.bk-nested-loading) {
        height: calc(100vh - 240px);
      }

      :deep(.bk-table) {
        height: 100% !important;

        .configs-head {
          padding-bottom: 2px;
          border-bottom: 1px dashed #313238;
        }

        .append-config-btn {
          display: none;
        }

        .is-custom {
          display: none;
        }

        tr {
          &:hover {
            .append-config-btn {
              display: inline-flex;
              margin-left: 8px;
            }

            .is-custom {
              display: inline;
              color: var(--primary-color);
              cursor: pointer;
            }
          }
        }

        .flow-node-action {
          display: inline-block;
          cursor: pointer;

          & ~ .flow-node-action {
            margin-left: 24px;
          }
        }
      }
    }
  }
</style>
