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
          @page-limit-change="handeChangeLimit"
          @page-value-change="handleChangePage">
          <BkTableColumn
            :label="t('单据类型')"
            :width="240">
            <template #default="{ data }">
              <TextOverflowLayout>
                {{ data.ticket_type_display }}
                <template #append>
                  <AuthButton
                    v-bk-tooltips="{
                      content: t('所有集群已免审批'),
                      disabled: data.configs.need_itsm,
                    }"
                    action-id="biz_ticket_config_set"
                    class="append-config-btn"
                    :disabled="!data.configs.need_itsm"
                    :permission="data.permission.biz_ticket_config_set"
                    :resource="dbType"
                    size="small"
                    @click="(event: PointerEvent) => handleShowAppendConfig(data, event)">
                    {{ t('添加免审批') }}
                  </AuthButton>
                </template>
              </TextOverflowLayout>
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
                    v-model:isShow="showEditConfig[data.id]"
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
                      v-model:isShow="showEditConfig[data.id]"
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
                {{ t('是') }}
              </span>
              <span
                v-else
                style="color: #ff9c01">
                {{ t('否') }}
              </span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="need_manual_confirm"
            :label="() => renderHead('need_manual_confirm')"
            :width="120">
            <template #default="{ data }">
              <span v-if="data.configs.need_manual_confirm">
                {{ t('是') }}
              </span>
              <span
                v-else
                style="color: #ff9c01">
                {{ t('否') }}
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
            :label="t('操作')"
            :width="100">
            <template #default="{ data }">
              <AuthButton
                v-bk-tooltips="{
                  content: t('内置目标不支持编辑'),
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
                  class="is-custom ml-8"
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

  import { useGlobalBizs } from '@stores';

  import type { DBTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import RenderRow from '@components/render-row/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import AppendConfigSide from './AppendConfigSide.vue';
  import DeleteConfig from "./DeleteConfig.vue";
  import EditConfig from './EditConfig.vue';

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
  const tableData = shallowRef<TicketFlowDescribeModel[]>([]);
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
      const ticketTypeMemo: Record<string, number> = {};
      tableData.value = data.results.reduce<TicketFlowDescribeModel[]>((acc, item, index) => {
        const existIndex = ticketTypeMemo[item.ticket_type];
        const row = {
          ..._.cloneDeep(item),
          updateAtDisplay: item.updateAtDisplay,
          isCustomTarget: item.isCustomTarget,
          isClusterTarget: item.isClusterTarget,
          clusterDomainList: item.clusterDomainList,
        }
        if (existIndex !== undefined) {
          acc.splice(existIndex, 1, row);
        } else {
          acc.push(row);
        }
        ticketTypeMemo[item.ticket_type] = index;
        return acc;
      }, []);
      isAnomalies.value = false;
    },
    onError() {
      pagination.value.count = 0;
      tableData.value = [];
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

  const handleShowAppendConfig = (data: TicketFlowDescribeModel, e: PointerEvent, isEdit = false) => {
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
