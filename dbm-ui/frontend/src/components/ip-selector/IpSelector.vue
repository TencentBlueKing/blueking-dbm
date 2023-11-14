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
    class="db-ip-selector"
    v-bind="$attrs">
    <div
      v-if="buttonText"
      class="db-ip-selector__operations">
      <div>
        <span
          v-bk-tooltips="buttonTips"
          class="inline-block">
          <BkButton
            v-if="buttonText"
            class="db-ip-selector__trigger"
            :disabled="!buttonTips.disabled"
            @click="handleShowIpSelector">
            <i class="db-icon-add" />
            {{ buttonText }}
          </BkButton>
        </span>
        <span class="db-ip-selector__desc">
          <slot name="desc" />
        </span>
      </div>
      <BkInput
        v-if="showPreview"
        v-model="selectorState.search"
        class="db-ip-selector__search"
        :placeholder="searchPlaceholder || $t('请输入IP')"
        type="search" />
    </div>
    <div
      v-if="showPreview"
      class="db-ip-selector__content">
      <slot>
        <BkLoading
          v-if="renderData.length > 0"
          :loading="selectorState.isLoading">
          <DBCollapseTable
            class="mt-16"
            :operations="operations"
            :table-props="dbCollapseTableTableData"
            :title="title" />
        </BkLoading>
        <PreviewWhitelist
          v-if="selectorState.selected?.dbm_whitelist?.length > 0"
          :data="selectorState.selected.dbm_whitelist"
          :search="selectorState.search"
          @clear-selected="handleClearSelected('dbm_whitelist')"
          @remove-selected="(index) => handleRemoveSelected(index, 'dbm_whitelist')" />
      </slot>
    </div>
  </div>
  <BkDialog
    v-model:is-show="showDialog"
    class="db-ip-selector-dialog"
    :close-icon="false"
    :esc-close="false"
    :quick-close="false"
    scrollable>
    <div
      v-if="cloudTips"
      style="padding: 8px 16px;">
      <BkAlert
        theme="info"
        :title="cloudTips" />
    </div>
    <BkIpSelector
      :config="{ panelList }"
      :disable-host-method="disableHostMethodHandler"
      :height="700"
      mode="section"
      :service="services"
      :single-host-select="singleHostSelect"
      :value="selectorState.selected"
      @change="handleChange" />
    <template #footer>
      <span class="mr24">
        <slot
          :host-list="selectorState.cacheSelected.host_list"
          name="submitTips" />
      </span>
      <span v-bk-tooltips="submitButtonDisabledInfo.tooltips">
        <BkButton
          :disabled="submitButtonDisabledInfo.disabled"
          theme="primary"
          @click="handleConfirmChange">
          {{ $t('确定') }}
        </BkButton>
      </span>
      <BkButton
        class="ml8"
        @click="handleCancelChange">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script lang="tsx">
  import type { TablePropTypes } from 'bkui-vue/lib/table/props';
  import _ from 'lodash';

  import {
    checkHost,
    getHostDetails,
    getHosts,
    getHostTopo,
  } from '@services/source/ipchooser';
  import type { HostDetails } from '@services/types/ip';
  import {
    getWhitelist,
  } from '@services/whitelist';

  import { useCopy, useFormItem } from '@hooks';

  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';
  import DbStatus from '@components/db-status/index.vue';

  import { t } from '@locales/index';

  import PreviewWhitelist from './components/PreviewWhitelist.vue';

  import type { TableColumnRender } from '@/types/bkui-vue';

  /** IP 选择器返回结果 */
  export type IPSelectorResult = {
    dynamic_group_list: any[],
    host_list: Array<Partial<HostDetails>>,
    node_list: any[],
    dbm_whitelist: any[],
  }

  type IPSelectorResultKey = keyof IPSelectorResult;
</script>

<script setup lang="tsx">
  interface Props {
    bizId: number | string,
    buttonText?: string,
    searchPlaceholder?: string,
    tableProps?: TablePropTypes,
    data?: HostDetails[],
    title?: string,
    showView?: boolean,
    required?: boolean,
    isCloudAreaRestrictions?: boolean,
    cloudInfo?: {id?: number | string, name?: string},
    disableDialogSubmitMethod?: (hostList: Array<any>) => string | boolean
    disableHostMethod?: (...args: any) => string | boolean,
    serviceMode?: 'all' | 'idle_only',
    panelList?: Array<'staticTopo' | 'manualInput' | 'dbmWhitelist'>,
    disableTips?: string,
    singleHostSelect: boolean
  }

  interface Emits {
    (e: 'change', value: typeof selectorState['tableData']): void
    (e: 'changeWhitelist', value: IPSelectorResult['dbm_whitelist']): void
  }

  const props = withDefaults(defineProps<Props>(), {
    buttonText: t('添加服务器'),
    searchPlaceholder: '',
    tableProps: () => ({} as TablePropTypes),
    data: () => [],
    title: t('静态拓扑'),
    showView: true,
    required: false,
    isCloudAreaRestrictions: true,
    cloudInfo: () => ({}),
    disableDialogSubmitMethod: () => false,
    disableHostMethod: () => false,
    serviceMode: 'idle_only',
    panelList: () => ['staticTopo', 'manualInput'],
    disableTips: '',
    singleHostSelect: false,
  });
  const emits = defineEmits<Emits>();

  const showDialog = defineModel<boolean>('showDialog', {
    default: false,
    local: true,
  });

  const copy = useCopy();
  const formItem = useFormItem();

  const cloudTips = computed(() => {
    if (Object.keys(props.cloudInfo).length === 0) return '';

    return t('已过滤出管控区域xx可选的主机', { name: props.cloudInfo.name });
  });
  const selectorState = reactive({
    selected: {
      dynamic_group_list: [],
      host_list: [],
      node_list: [],
      dbm_whitelist: [],
    } as IPSelectorResult,
    cacheSelected: {
      dynamic_group_list: [],
      host_list: [],
      node_list: [],
      dbm_whitelist: [],
    } as IPSelectorResult,
    isLoading: false,
    tableData: [] as any[],
    search: '',
  });
  // ip 选择器预览表格 props
  const previewTableProps = computed(() => {
    const tableProps = props.tableProps || {};
    if (Object.keys(tableProps).length === 0) {
      return initTableProps();
    }
    return tableProps;
  });

  const dbCollapseTableTableData = computed(() => ({
    ...previewTableProps.value,
    data: renderData.value,
  })) as unknown as TablePropTypes;

  const buttonTips = computed(() => {
    const tips = {
      disabled: true,
      content: '',
    };

    if (props.disableTips) {
      tips.disabled = false;
      tips.content = props.disableTips;
      return tips;
    }

    if (!props.bizId) {
      tips.disabled = false;
      tips.content = t('请选择业务');
      return tips;
    }

    const { id } = props.cloudInfo;
    if (props.isCloudAreaRestrictions && (id === '' || id === undefined || Number(id) < 0)) {
      tips.disabled = false;
      tips.content = t('请选择管控区域');
      return tips;
    }

    return tips;
  });

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        disabled: true,
        content: '',
      },
    };

    if (props.required && selectorState.cacheSelected.host_list.length < 1) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = t('请选择主机');
      return info;
    }

    const checkValue = props.disableDialogSubmitMethod(selectorState.cacheSelected.host_list);
    if (checkValue) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = _.isString(checkValue) ? checkValue : t('无法保存');
    }
    return info;
  });

  const disableHostMethodHandler = (data: any, selected: any[]) => {
    if (data.alive === 0) {
      return t('Agent异常无法使用');
    }
    return props.disableHostMethod(data, selected);
  };

  // ip 选择器 scope 参数
  const scope = computed<{ scope_id: number, scope_type: string, bk_cloud_id?: number}>(() => {
    const params = {
      scope_id: props.bizId as number,
      scope_type: 'biz',
    };
    if (_.isNumber(props.cloudInfo.id)) {
      Object.assign(params, {
        bk_cloud_id: props.cloudInfo.id,
      });
    }
    return params;
  });
  // 设置 ip 选择器接口参数
  const services = {
    fetchTopologyHostCount: (node: any) => getHostTopo({
      mode: props.serviceMode,
      all_scope: true,
      // scope_list: !node ? [] : [node.meta],
      scope_list: [scope.value],
    }),
    fetchHostsDetails: (params: any) => {
      const firstHost = params.host_list[0];
      return getHostDetails({
        mode: props.serviceMode,
        // scope_list: [firstHost.meta],
        scope_list: [scope.value],
        ...params,
      });
    },
    fetchHostCheck: (params: any) => checkHost({
      mode: props.serviceMode,
      scope_list: [scope.value],
      bk_cloud_id: props.cloudInfo?.id,
      ...params,
    }),
    fetchTopologyHostsNodes: (params: any) => getHosts({
      mode: props.serviceMode,
      bk_cloud_id: props.cloudInfo?.id,
      ...params,
    }),
    fetchDBMWhitelist: (params: any) => getWhitelist({ bk_biz_id: props.bizId, ...params }).then(res => res.results),
  };
  // 显示自定义预览选中数据
  const showPreview = computed(() => (
    props.showView
    && (selectorState.selected.host_list.length > 0 || selectorState.selected?.dbm_whitelist?.length > 0)
  ));
  // 过滤表格数据
  const renderData = computed(() => {
    if (selectorState.search) {
      return selectorState.tableData.filter((item: any) => (
        item.ip.includes(selectorState.search) || item.ipv6.includes(selectorState.search)
      ));
    }
    return selectorState.tableData;
  });

  // IP 操作
  const operations = [
    {
      label: t('清除所有'),
      onClick: () => handleClearSelected('host_list'),
    },
    {
      label: t('清除异常IP'),
      onClick: () => {
        const removeData = _.remove(selectorState.tableData, (item: any) => item.alive === 0);
        // 删除异常IP
        _.pullAllBy(selectorState.selected.host_list, removeData, 'host_id');
        handleEmitsChange();
      },
    },
    {
      label: t('复制所有IP'),
      onClick: () => {
        const ips = selectorState.selected.host_list.map((item: any) => item.ip);
        copy(ips.join('\n'));
      },
    },
    {
      label: t('复制异常IP'),
      onClick: () => {
        const abnormalHosts = selectorState.selected.host_list.filter((item: any) => item.alive === 0);
        const abnormalIps = abnormalHosts.map((item: any) => item.ip);
        copy(abnormalIps.join('\n'));
      },
    }];

  // 处理选中列表中添加额外的数据操作
  watch(() => props.data, (data) => {
    const cloneData = _.cloneDeep(data);
    const hostList = cloneData.map(item => ({
      host_id: item.host_id,
      ip: item.ip,
      ipv6: item.ipv6,
      meta: item.meta,
    }));
    selectorState.selected.host_list = [...hostList];
    selectorState.cacheSelected.host_list = [...hostList];
    selectorState.tableData = cloneData;
  }, { immediate: true, deep: true });

  /**
   * ip 选择器预览表默认配置
   */
  function initTableProps() {
    const columns = [
      {
        label: 'IP',
        field: 'ip',
      },
      {
        label: t('管控区域'),
        field: 'cloud_area',
        render: ({ cell }: any) => <span>{cell?.name || '--'}</span>,
      },
      {
        label: t('Agent状态'),
        field: 'alive',
        render: ({ cell }: { cell: number }) => {
          const info = cell === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        label: t('主机名称'),
        field: 'host_name',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: t('OS名称'),
        field: 'os_name',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: t('所属云厂商'),
        field: 'cloud_vendor',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: t('OS类型'),
        field: 'os_type',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: t('主机ID'),
        field: 'host_id',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: 'Agent ID',
        field: 'agent_id',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: 'IPv6',
        field: 'ipv6',
        render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
      },
      {
        label: t('操作'),
        field: 'operation',
        width: 100,
        render: ({ index }: TableColumnRender) => (
          <bk-button
            text
            theme="primary"
            onClick={() => handleRemoveSelected(index)}>
            { t('删除') }
          </bk-button>
        ),
      },
    ];
    const checked = ['ip', 'host_name', 'alive', 'operation'];
    const disabledKeys = ['ip', 'operation'];
    return {
      maxHeight: 474,
      columns,
      settings: {
        fields: columns.map(item => ({
          label: item.label,
          field: item.field,
          disabled: disabledKeys.includes(item.field),
        })),
        checked,
      },
      pagination: {
        count: 0,
        current: 1,
        limit: 10,
        limitList: [10, 20, 50, 100],
        align: 'right',
        layout: ['total', 'limit', 'list'],
      },
    };
  }

  /**
   * 清空已经选中列表
   */
  function handleClearSelected(key: IPSelectorResultKey = 'host_list') {
    selectorState.selected[key].splice(0, Number.MAX_SAFE_INTEGER);
    selectorState.cacheSelected[key].splice(0, Number.MAX_SAFE_INTEGER);
    if (key === 'host_list') {
      selectorState.tableData.splice(0, Number.MAX_SAFE_INTEGER);
    }
    handleEmitsChange();
  }

  /**
   * 移除选中项
   */
  function handleRemoveSelected(index: number, key: IPSelectorResultKey = 'host_list') {
    selectorState.selected[key].splice(index, 1);
    selectorState.cacheSelected[key].splice(index, 1);
    if (key === 'host_list') {
      selectorState.tableData.splice(index, 1);
    }
    handleEmitsChange();
  }

  /**
   * 获取主机详情
   */
  function fetchHostDetails() {
    if (selectorState.selected.host_list.length === 0) return;

    const firstHost = selectorState.selected.host_list[0];

    const params = {
      mode: props.serviceMode,
      host_list: selectorState.selected.host_list.map(item => ({
        host_id: item.host_id,
        meta: {
          bk_biz_id: props.bizId as number,
          scope_id: props.bizId as number,
          scope_type: 'biz',
        },
      })),
      scope_list: firstHost.meta ? [firstHost.meta] : [],
    };
    selectorState.isLoading = true;
    getHostDetails(params)
      .then((res) => {
        selectorState.tableData = res;
        handleEmitsChange();
      })
      .finally(() => {
        selectorState.isLoading = false;
      });
  }

  /**
   * ip 选择变更
   */
  function handleChange(result: IPSelectorResult) {
    selectorState.cacheSelected = result;
  }

  /**
   * 确认 ip 选择器数据变更
   */
  function handleConfirmChange() {
    const result = _.cloneDeep(selectorState.cacheSelected);
    selectorState.selected = result;
    if (result.host_list.length === 0) {
      handleClearSelected();
    }
    fetchHostDetails();
    showDialog.value = false;
  }

  function handleCancelChange() {
    selectorState.cacheSelected = _.cloneDeep(selectorState.selected);
    showDialog.value = false;
  }

  /**
   * 触发变更
   */
  function handleEmitsChange() {
    emits('change', _.cloneDeep(selectorState.tableData));
    emits('changeWhitelist', _.cloneDeep(selectorState.selected.dbm_whitelist));
    nextTick(() => {
      formItem?.validate?.();
    });
  }

  function handleShowIpSelector() {
    if (!props.bizId) {
      return;
    }
    showDialog.value = true;
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .db-ip-selector {
    &__operations {
      justify-content: space-between;
      .flex-center();
    }

    &__desc {
      padding-left: 12px;
      font-size: @font-size-mini;
      line-height: 20px;
      color: @default-color;
    }

    &__trigger {
      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
      }

      &.is-disabled {
        .db-icon-add {
          color: @disable-color;
        }
      }
    }

    &__search {
      width: 320px;
    }

    &-dialog {
      width: 80%;
      max-width: 1600px;
      min-width: 1200px;

      :deep(.bk-modal-header) {
        display: none;
      }

      :deep(.bk-modal-content) {
        height: unset;
        max-height: unset;
        min-height: unset;
        padding: 0;
        overflow: hidden !important;
      }

      :deep(.bk-modal-footer) {
        border-top: 0;
      }

      :deep(.bk-button) {
        min-width: 88px;
      }
    }
  }
</style>
