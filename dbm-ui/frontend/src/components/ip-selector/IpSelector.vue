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
          @remove-selected="(index: number) => handleRemoveSelected(index, 'dbm_whitelist')" />
      </slot>
    </div>
  </div>
  <BkDialog
    v-model:is-show="showDialog"
    class="db-ip-selector-dialog"
    :close-icon="false"
    :esc-close="false"
    :quick-close="false"
    scrollable
    width="80%">
    <div
      v-if="cloudTips"
      style="padding: 8px 16px">
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

  import { checkHost, getHostDetails, getHosts, getHostTopo } from '@services/source/ipchooser';
  import { getWhitelist } from '@services/source/whitelist';
  import type { HostInfo } from '@services/types';

  import { useFormItem } from '@hooks';

  import { OSTypes } from '@common/const';

  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';
  import DbStatus from '@components/db-status/index.vue';

  import { execCopy } from '@utils';

  import { t } from '@locales/index';

  import PreviewWhitelist from './components/PreviewWhitelist.vue';

  /** IP 选择器返回结果 */
  export type IPSelectorResult = {
    dbm_whitelist: any[];
    dynamic_group_list: any[];
    host_list: Array<HostInfo>;
    node_list: any[];
  };

  type IPSelectorResultKey = keyof IPSelectorResult;

  interface Props {
    bizId: number | string;
    buttonText?: string;
    cloudInfo?: { id?: number | string; name?: string };
    data?: HostInfo[];
    disableDialogSubmitMethod?: (hostList: Array<any>) => string | boolean;
    disableHostMethod?: (...args: any) => string | boolean;
    disableTips?: string;
    isCloudAreaRestrictions?: boolean;
    onlyAliveHost?: boolean;
    osTypes?: OSTypes[];
    panelList?: Array<'staticTopo' | 'manualInput' | 'dbmWhitelist'>;
    required?: boolean;
    searchPlaceholder?: string;
    serviceMode?: 'all' | 'idle_only';
    showView?: boolean;
    singleHostSelect?: boolean;
    tableProps?: TablePropTypes;
    title?: string;
  }

  interface Emits {
    (e: 'change', value: any[]): void;
    (e: 'changeWhitelist', value: IPSelectorResult['dbm_whitelist']): void;
  }
</script>

<script setup lang="tsx">
  const props = withDefaults(defineProps<Props>(), {
    buttonText: t('添加服务器'),
    cloudInfo: () => ({}),
    data: () => [],
    disableDialogSubmitMethod: () => false,
    disableHostMethod: () => false,
    disableTips: '',
    isCloudAreaRestrictions: true,
    onlyAliveHost: true,
    osTypes: () => [],
    panelList: () => ['staticTopo', 'manualInput'],
    required: false,
    searchPlaceholder: '',
    serviceMode: 'idle_only',
    showView: true,
    singleHostSelect: false,
    tableProps: () => ({}) as TablePropTypes,
    title: t('静态拓扑'),
  });
  const emits = defineEmits<Emits>();

  const showDialog = defineModel<boolean>('showDialog', {
    default: false,
  });

  const formItem = useFormItem();

  const cloudTips = computed(() => {
    if (Object.keys(props.cloudInfo).length === 0) return '';

    return t('已过滤出管控区域xx可选的主机', { name: props.cloudInfo.name });
  });
  const selectorState = reactive({
    cacheSelected: {
      dbm_whitelist: [],
      dynamic_group_list: [],
      host_list: [],
      node_list: [],
    } as IPSelectorResult,
    isLoading: false,
    search: '',
    selected: {
      dbm_whitelist: [],
      dynamic_group_list: [],
      host_list: [],
      node_list: [],
    } as IPSelectorResult,
    tableData: [] as any[],
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
    pagination: previewTableProps.value.pagination
      ? {
          ...(previewTableProps.value.pagination as Exclude<TablePropTypes['pagination'], boolean>),
          count: renderData.value.length,
        }
      : previewTableProps.value.pagination,
  })) as unknown as TablePropTypes;

  const buttonTips = computed(() => {
    const tips = {
      content: '',
      disabled: true,
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
        content: '',
        disabled: true,
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
    if (props.onlyAliveHost && data.alive !== 1) {
      return t('Agent异常无法使用');
    }
    if (props.osTypes.length > 0 && !props.osTypes.includes(Number(data.os_type))) {
      return t('xx机器无法使用', [OSTypes[Number(data.os_type)]]);
    }
    return props.disableHostMethod(data, selected);
  };

  // ip 选择器 scope 参数
  const scope = computed<{ bk_cloud_id?: number; scope_id: number; scope_type: string }>(() => {
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
    fetchDBMWhitelist: (params: any) => getWhitelist({ bk_biz_id: props.bizId, ...params }).then((res) => res.results),
    fetchHostCheck: (params: any) =>
      checkHost({
        bk_cloud_id: props.cloudInfo?.id,
        mode: props.serviceMode,
        scope_list: [scope.value],
        ...params,
      }),
    fetchHostsDetails: (params: any) => {
      const firstHost = params.host_list[0];
      return getHostDetails({
        mode: props.serviceMode,
        scope_list: [scope.value],
        ...params,
      });
    },
    fetchTopologyHostCount: (node: any) =>
      getHostTopo({
        all_scope: true,
        mode: props.serviceMode,
        scope_list: [scope.value],
      }),
    fetchTopologyHostsNodes: (params: any) =>
      getHosts({
        bk_cloud_id: props.cloudInfo?.id,
        mode: props.serviceMode,
        ...params,
      }),
  };
  // 显示自定义预览选中数据
  const showPreview = computed(
    () =>
      props.showView &&
      (selectorState.selected.host_list.length > 0 || selectorState.selected?.dbm_whitelist?.length > 0),
  );
  // 过滤表格数据
  const renderData = computed(() => {
    if (selectorState.search) {
      return selectorState.tableData.filter(
        (item: any) => item.ip.includes(selectorState.search) || item.ipv6.includes(selectorState.search),
      );
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
        copy(ips);
      },
    },
    {
      label: t('复制异常IP'),
      onClick: () => {
        const abnormalHosts = selectorState.selected.host_list.filter((item: any) => item.alive === 0);
        const abnormalIps = abnormalHosts.map((item: any) => item.ip);
        copy(abnormalIps);
      },
    },
  ];

  // 处理选中列表中添加额外的数据操作
  watch(
    () => props.data,
    (data) => {
      const cloneData = _.cloneDeep(data);
      selectorState.selected.host_list = [...cloneData];
      selectorState.cacheSelected.host_list = [...cloneData];
      selectorState.tableData = [...cloneData];
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const copy = (list: string[]) => {
    execCopy(list.join('\n'), t('复制成功，共n条', { n: list.length }));
  };

  /**
   * ip 选择器预览表默认配置
   */
  function initTableProps() {
    const columns = [
      {
        field: 'ip',
        label: 'IP',
      },
      {
        field: 'cloud_area',
        label: t('管控区域'),
        render: ({ data }: { data: HostInfo }) => data.cloud_area.name || '--',
      },
      {
        field: 'alive',
        label: t('Agent状态'),
        render: ({ data }: { data: HostInfo }) => {
          const info = data.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        field: 'host_name',
        label: t('主机名称'),
        render: ({ data }: { data: HostInfo }) => data.host_name || '--',
      },
      {
        field: 'os_name',
        label: t('OS名称'),
        render: ({ data }: { data: HostInfo }) => data.os_name || '--',
      },
      {
        field: 'cloud_vendor',
        label: t('所属云厂商'),
        render: ({ data }: { data: HostInfo }) => data.cloud_vendor || '--',
      },
      {
        field: 'os_type',
        label: t('OS类型'),
        render: ({ data }: { data: HostInfo }) => data.os_type || '--',
      },
      {
        field: 'host_id',
        label: t('主机ID'),
        render: ({ data }: { data: HostInfo }) => data.host_id || '--',
      },
      {
        field: 'agent_id',
        label: 'Agent ID',
        render: ({ data }: { data: HostInfo }) => data.agent_id || '--',
      },
      {
        field: 'ipv6',
        label: 'IPv6',
        render: ({ data }: { data: HostInfo }) => data.ipv6 || '--',
      },
      {
        field: 'operation',
        label: t('操作'),
        render: ({ index }: { index: number }) => (
          <bk-button
            theme='primary'
            text
            onClick={() => handleRemoveSelected(index)}>
            {t('删除')}
          </bk-button>
        ),
        width: 100,
      },
    ];
    const checked = ['ip', 'host_name', 'alive', 'operation'];
    const disabledKeys = ['ip', 'operation'];
    return {
      columns,
      maxHeight: 474,
      pagination: {
        align: 'right',
        count: 0,
        current: 1,
        layout: ['total', 'limit', 'list'],
        limit: 10,
        limitList: [10, 20, 50, 100],
      },
      settings: {
        checked,
        fields: columns.map((item) => ({
          disabled: disabledKeys.includes(item.field),
          field: item.field,
          label: item.label,
        })),
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
      host_list: selectorState.selected.host_list.map((item) => ({
        host_id: item.host_id,
        meta: {
          bk_biz_id: props.bizId as number,
          scope_id: `${props.bizId}`,
          scope_type: 'biz',
        },
      })),
      mode: props.serviceMode,
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
  @import '@styles/mixins.less';

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

      :deep(.bk-dialog-content) {
        padding: 0;
        margin: 0;
      }

      :deep(.bk-button) {
        min-width: 88px;
      }
    }
  }
</style>
