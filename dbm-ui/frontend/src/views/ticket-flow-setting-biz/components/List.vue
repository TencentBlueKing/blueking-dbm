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
        {{ t('内置策略为平台预设的审批规则，不可修改。根据业务需求，您可对全部或部分集群应用免审批策略。') }}
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
          row-key="rowKey"
          @page-limit-change="handeChangeLimit"
          @page-value-change="handleChangePage">
          <BkTableColumn
            fixed="left"
            :label="t('单据类型')"
            :rowspan="rowSpan"
            :width="240">
            <template #default="{ data }">
              {{ data.ticket_type_display }}
              <AuthButton
                v-bk-tooltips="{
                  content: appendBtnTipMap[appendBtnController[data.ticket_type]],
                  disabled: !appendBtnController[data.ticket_type],
                }"
                action-id="biz_ticket_config_set"
                class="append-config-btn"
                :disabled="appendBtnController[data.ticket_type]"
                :permission="data.permission.biz_ticket_config_set"
                :resource="dbType"
                size="small"
                @click="(event: PointerEvent) => handleShowAppendConfig(data, event)">
                {{ t('添加免审批') }}
              </AuthButton>
            </template>
          </BkTableColumn>
          <BkTableColumn
            :label="t('目标')"
            :width="200">
            <template #default="{ data }">
              <RenderRow
                v-if="data.isClusterTarget"
                :data="data.clusterDomainList"
                show-all>
                <template #prepend>
                  <span class="mr-4"> {{ t('集群') }} : </span>
                </template>
                <template #append>
                  <BkTag
                    class="ml-4"
                    size="small"
                    theme="success">
                    {{ t('自定义') }}
                  </BkTag>
                  <EditConfig
                    v-model:is-show="showEditConfig[data.id]"
                    :data="data"
                    @success="fetchData">
                    <AuthButton
                      action-id="biz_ticket_config_set"
                      class="is-custom"
                      :permission="data.permission.biz_ticket_config_set"
                      :resource="dbType"
                      text
                      @click="() => (showEditConfig[data.id] = true)">
                      <DbIcon
                        v-bk-tooltips="t('修改目标')"
                        type="bk-dbm-icon db-icon-edit" />
                    </AuthButton>
                  </EditConfig>
                </template>
              </RenderRow>
              <TextOverflowLayout v-else>
                {{ t('业务下全部对象') }}
                <template #append>
                  <div v-if="data.isCustomTarget">
                    <BkTag
                      class="ml-4"
                      size="small"
                      theme="success">
                      {{ t('自定义') }}
                    </BkTag>
                    <EditConfig
                      v-model:is-show="showEditConfig[data.id]"
                      :data="data"
                      @success="fetchData">
                      <AuthButton
                        action-id="biz_ticket_config_set"
                        class="is-custom"
                        :permission="data.permission.biz_ticket_config_set"
                        :resource="dbType"
                        text
                        @click="() => (showEditConfig[data.id] = true)">
                        <DbIcon
                          v-bk-tooltips="t('修改目标')"
                          type="bk-dbm-icon db-icon-edit" />
                      </AuthButton>
                    </EditConfig>
                  </div>
                  <BkTag
                    v-else
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
            :label="() => renderHead('need_itsm')"
            :width="120">
            <template #default="{ data }">
              <span v-if="data.configs.need_itsm">
                {{ t('需审批') }}
              </span>
              <span
                v-else
                style="color: #ff9c01">
                {{ t('免审批') }}
              </span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="need_manual_confirm"
            :label="() => renderHead('need_manual_confirm')"
            :width="120">
            <template #default="{ data }">
              <span v-if="data.configs.need_manual_confirm">
                {{ t('需确认') }}
              </span>
              <span
                v-else
                style="color: #ff9c01">
                {{ t('免确认') }}
              </span>
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
            fixed="right"
            :label="t('操作')"
            :width="100">
            <template #default="{ data }">
              <AuthButton
                v-bk-tooltips="{
                  content: t('内置策略不支持编辑'),
                  disabled: data.isCustomTarget,
                }"
                action-id="biz_ticket_config_set"
                :disabled="!data.isCustomTarget"
                :permission="data.permission.biz_ticket_config_set"
                :resource="dbType"
                text
                theme="primary"
                @click="(event: PointerEvent) => handleShowAppendConfig(data, event, true)">
                {{ t('编辑') }}
              </AuthButton>
              <DeleteConfig
                v-if="data.isCustomTarget"
                v-model="data.id"
                :data="data"
                @success="fetchData">
                <AuthButton
                  action-id="biz_ticket_config_set"
                  class="ml-16"
                  :permission="data.permission.biz_ticket_config_set"
                  :resource="dbType"
                  text
                  theme="primary">
                  {{ t('删除') }}
                </AuthButton>
              </DeleteConfig>
            </template>
          </BkTableColumn>
          <template #empty>
            <EmptyStatus
              :is-anomalies="isAnomalies"
              :is-searching="searchValue.length > 0"
              @clear-search="handleClearSearch"
              @refresh="fetchData" />
          </template>
        </BkTable>
      </BkLoading>
    </div>
  </div>
  <AppendConfigSide
    v-model:is-show="appendConfig.isShow"
    :data="appendConfig.data"
    :is-edit="appendConfig.isEdit"
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

  import { useGlobalBizs } from '@stores';

  import type { DBTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { random } from '@utils';

  import AppendConfigSide from './AppendConfigSide.vue';
  import DeleteConfig from "./DeleteConfig.vue";
  import EditConfig from './EditConfig.vue';

  interface IDataRow extends TicketFlowDescribeModel {
    rowSpan: number;
  }

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const ticketTypeList = shallowRef<ISearchItem[]>([]);
  const searchValue = ref<Array<ISearchItem & { values: ISearchItem[] }>>([]);
  const showEditConfig = ref<Record<string, boolean>>({});
  const isAnomalies = ref(false);
  const pagination = ref(useDefaultPagination());
  const allTableData = shallowRef<IDataRow[]>([]);
  const appendConfig = reactive({
    isShow: false,
    isEdit: false,
    data: {} as TicketFlowDescribeModel,
  });
  /*
  * 单据类型下是否所有集群已免审批
  * 0、非免审批
  * 1、部分集群免审批
  * 2、所有集群免审批
  * 非0都禁用追加按钮
  */
  const appendBtnController = ref<Record<string, 0 | 1 | 2>>({});
  const appendBtnTipMap = {
    0: '',
    1: t('已存在自定义的免审批'),
    2: t('所有集群已免审批'),
  }

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
      appendBtnController.value = {};
      allTableData.value = Object.values(resultsMap).flatMap(values => {
        const hasCurrentBizTarget = values.some((item) => item.isCurrentBizTarget);
        const rows = values.reduce<TicketFlowDescribeModel[]>((acc, item) => {
          const level = Math.max(
            // 业务目标和全局（内置）目标，且是否审批为免审批状态，禁用等级为2，否则不禁用
            (item.isCurrentBizTarget || item.isDefaultTarget ) && !item.configs.need_itsm ? 2 : 0,
            // 集群目标，且是否审批为免审批状态，禁用等级为1，否则不禁用
            item.isClusterTarget && !item.configs.need_itsm ? 1 : 0
          );
          appendBtnController.value[item.ticket_type] = Math.max(
            appendBtnController.value[item.ticket_type] ?? 0,
            level
          ) as 0 | 1 | 2;

          // 1、存在多条生效策略
          // 2、存在业务全部目标
          // 3、满足前两条，且当前为内置目标，隐藏内置目标
          const isHidden = values.length > 1 && hasCurrentBizTarget && item.isDefaultTarget;
          if (!isHidden) {
            acc.push(item);
          }
          return acc;
        }, []);
        rows.sort((_, b) => b.isClusterTarget ? 1 : -1);// 集群目标排前面;
        const result = rows.map((item) => ({
          ..._.cloneDeep(item),
          rowKey: random(),
          updateAtDisplay: item.updateAtDisplay,
          isDefaultTarget: item.isDefaultTarget,
          isCustomTarget: item.isCustomTarget,
          isClusterTarget: item.isClusterTarget,
          isCurrentBizTarget: item.isCurrentBizTarget,
          clusterDomainList: item.clusterDomainList,
          rowSpan: rows.length
        }));
        return result;
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
      bk_biz_id: currentBizId,
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
        bk_biz_id: currentBizId,
        cluster_ids: [],
        configs: {
          need_itsm: false,
          need_manual_confirm: cloneData.configs.need_manual_confirm,
        },
      });
    } else {
      appendConfig.data = cloneData;
    }
    appendConfig.isEdit = isEdit;
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

        tr {
          &:hover {
            .append-config-btn {
              display: inline-flex;
              margin-left: 8px;
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
