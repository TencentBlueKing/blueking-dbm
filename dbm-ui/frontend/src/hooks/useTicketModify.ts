/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import _ from 'lodash';
import type { ComputedRef, InjectionKey, Ref, ShallowRef } from 'vue';
import { useI18n } from 'vue-i18n';

import TicketModifyRecordModel, { type TicketModifyMode } from '@services/model/ticket/modify-record';
import TicketModel from '@services/model/ticket/ticket';
import { getInfrasSubzonesByCity } from '@services/source/infras';
import { getCloudList } from '@services/source/ipchooser';
import { getRegions } from '@services/source/kubernetesToolbox';
import { listTag } from '@services/source/tag';
import { getTicketDetails } from '@services/source/ticket';

import { useUserProfile } from '@stores';

import { TicketTypes } from '@common/const';

import { getTicketModifyDiffOptions, isTicketModifiable } from '@views/ticket-center/common/ticket-modify/registry';
import { diffDetails, type DiffItem, formatValue } from '@views/ticket-center/common/ticket-modify/utils';

import { messageError } from '@utils';

export interface TicketModifyState {
  // 回到单据详情：从详情进入的返回上一页，直接打开改单链接的跳到单据详情页
  backToTicket: () => void;
  // 提交前确认弹窗，由 TicketModifyAlert 渲染
  confirmState: {
    diffList: DiffItem[];
    isShow: boolean;
    // 弹窗内提交按钮 loading，提交请求进行中为 true
    isSubmitting: boolean;
    // 弹窗关闭（取消，或提交成功）时结束 openConfirm 返回的 Promise
    resolve?: () => void;
    // 点击弹窗提交按钮时执行的提交动作，reject 时弹窗保持打开
    submit?: () => Promise<unknown>;
  };
  // 提交前确认弹窗标题，按改单模式区分
  confirmTitle: string;
  // 改后 details 与进入时的单据内容对比，提交时的变更计数与「重置」置灰共用这一份判据
  getDiffList: (details: unknown) => DiffItem[];
  // 改后补充信息（交付通知、单据备注）与进入时的单据对比，重新编辑、代为修改提交时使用
  getSupplementDiffList: (config: unknown, ticketRemark: string) => DiffItem[];
  isAdjustApply: boolean;
  isModify: boolean;
  // 提单人对自己的单据代为修改，提交后自动确认
  isSelfOnBehalf: ComputedRef<boolean>;
  mode: TicketModifyMode | '';
  modifyRemark: Ref<string>;
  // 打开确认弹窗；submit 在点击弹窗提交按钮时执行，弹窗关闭（取消或提交成功）后 Promise 结束
  openConfirm: (diffList: DiffItem[], submit: () => Promise<unknown>) => Promise<void>;
  // 提交时单据已被他人更新：关闭确认弹窗，改为提示「单据已更新」，只能返回单据
  openUpdated: (operator: string, time: string) => void;
  // 「重置」确认文案：改单模式下重置是丢弃本次修改、回到单据当前内容，不是清空；非改单为空，用各页默认文案
  resetContent: string;
  submitText: string;
  // 进入工具页时的单据，details 为对比基准，version 为提交时校验的内容版本
  ticketData: ShallowRef<TicketModel | undefined>;
  // 「单据已更新」弹窗，由 TicketModifyAlert 渲染；operator / time 为最后一次更新单据的人和时间
  updatedState: {
    isShow: boolean;
    operator: string;
    time: string;
  };
  // 修改说明校验，由 TicketModifyRemark 挂载时注册；重新编辑模式没有修改说明，默认直接通过
  validateRemark: () => Promise<unknown>;
}

export const ticketModifyStateKey: InjectionKey<TicketModifyState> = Symbol('ticketModifyState');

const MODIFY_MODE_LIST: TicketModifyMode[] = [
  TicketModifyRecordModel.MODE_ON_BEHALF,
  TicketModifyRecordModel.MODE_RE_EDIT,
  TicketModifyRecordModel.MODE_ADJUST_APPLY,
];

/**
 * 改单工具页模式：申请页路由带 ticketId + modifyMode 进入。
 * 由 useApplyBase 调用并 provide，Alert、修改说明、业务选择等子组件用 useTicketModifyState 读取，
 * 保证一页只拉一次单据、只做一次进入拦截
 */
export const useTicketModify = () => {
  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { isSuperuser, username } = useUserProfile();

  const ticketId = Number(route.query.ticketId);
  const mode = MODIFY_MODE_LIST.find((item) => item === route.query.modifyMode) || '';
  // 没有 modifyMode 时是普通提单或「再次提单」，行为不变
  const isModify = Boolean(mode && ticketId);

  // 带了改单模式却没有单据 id，无法回填原单据内容，提示后回到单据列表
  if (mode && !ticketId) {
    messageError(t('缺少单据信息，无法进入改单'));
    router.replace({
      name: 'bizTicketManage',
    });
  }

  const ticketData = shallowRef<TicketModel>();
  // 以下映射只用于变更对比把 id / 代码展示为名称；列表未就绪或数据已下线时展示原值
  // 园区 id → 名称；不传城市返回全部园区，改前改后可能跨城市
  const subzoneNameMap = shallowRef<Record<number, string>>({});
  // 管控区域 id → 名称
  const cloudNameMap = shallowRef<Record<number, string>>({});
  // K8s 地域代码 → 名称，共享集群与业务独占集群的地域合并
  const regionNameMap = shallowRef<Record<string, string>>({});
  // 资源标签 id → 名称，只补单据快照里缺 label_names 的角色（API / MCP 建的单据）
  const labelNameMap = shallowRef<Record<string, string>>({});
  const modifyRemark = ref('');
  const confirmState = reactive<TicketModifyState['confirmState']>({
    diffList: [],
    isShow: false,
    isSubmitting: false,
  });
  const updatedState = reactive<TicketModifyState['updatedState']>({
    isShow: false,
    operator: '',
    time: '',
  });

  const submitTextMap: Record<TicketModifyMode, string> = {
    [TicketModifyRecordModel.MODE_ADJUST_APPLY]: t('提交调整'),
    [TicketModifyRecordModel.MODE_ON_BEHALF]: t('提交修改'),
    [TicketModifyRecordModel.MODE_RE_EDIT]: t('重新提交'),
  };

  // 提交前确认弹窗标题，与工具页主按钮一一对应
  const confirmTitleMap: Record<TicketModifyMode, string> = {
    [TicketModifyRecordModel.MODE_ADJUST_APPLY]: t('确认提交调整'),
    [TicketModifyRecordModel.MODE_ON_BEHALF]: t('确认提交修改'),
    [TicketModifyRecordModel.MODE_RE_EDIT]: t('确认重新提交'),
  };

  const backToDetail = () => {
    router.replace({
      name: 'ticketDetail',
      params: {
        ticketId,
      },
    });
  };

  /**
   * 从单据详情（详情页或列表侧栏）进入时，入口在当前页跳转，返回上一页即回到原来的详情位置；
   * 直接打开改单链接、没有上一页时，跳到单据详情页
   */
  const backToTicket = () => {
    if (window.history.state?.back) {
      router.back();
      return;
    }
    backToDetail();
  };

  // 进入拦截只用于提前挡住无效进入，最终以后端提交时的校验为准
  const checkEntry = (data: TicketModel) => {
    if (!isTicketModifiable(data.ticket_type)) {
      return false;
    }
    const isOperator = data.todo_operators.includes(username) || data.todo_helpers.includes(username);
    const ruleMap: Record<TicketModifyMode, { hasPermission: boolean; status: string[] }> = {
      [TicketModifyRecordModel.MODE_ADJUST_APPLY]: {
        hasPermission: isSuperuser || isOperator,
        status: [TicketModel.STATUS_RESOURCE_REPLENISH],
      },
      [TicketModifyRecordModel.MODE_ON_BEHALF]: {
        hasPermission: isOperator || (isSuperuser && data.todo_helpers.includes('admin')),
        status: [TicketModel.STATUS_APPROVE],
      },
      [TicketModifyRecordModel.MODE_RE_EDIT]: {
        hasPermission: data.creator === username,
        status: [TicketModel.STATUS_APPROVE, TicketModel.STATUS_CONFIRM_PENDING],
      },
    };
    const rule = ruleMap[mode as TicketModifyMode];
    if (!rule.status.includes(data.status)) {
      messageError(t('单据状态已变更为{status}', { status: data.statusText }));
      return false;
    }
    if (!rule.hasPermission) {
      messageError(t('您没有该单据的改单权限'));
      return false;
    }
    return true;
  };

  const K8S_TICKET_TYPES: TicketTypes[] = [
    TicketTypes.K8S_QDRANT_HA_APPLY,
    TicketTypes.K8S_SURREALDB_HA_APPLY,
    TicketTypes.K8S_SURREALDB_SINGLE_APPLY,
  ];

  /**
   * 按单据补齐依赖单据内容的名称映射：K8s 地域按业务取，资源标签按快照里缺名称的标签 id 取
   */
  const fetchTicketNameMaps = (data: TicketModel) => {
    if (K8S_TICKET_TYPES.includes(data.ticket_type) && data.bk_biz_id) {
      // 共享 / 独占两种部署类型的可选地域不同，改单可能在两者间切换，两份都取
      Promise.all([
        getRegions({ bkBizId: data.bk_biz_id, isPublic: true }),
        getRegions({ bkBizId: data.bk_biz_id, isPublic: false }),
      ]).then((lists) => {
        regionNameMap.value = Object.fromEntries(lists.flat().map((item) => [item.regionCode, item.regionName]));
      });
    }
    const resourceSpec = (
      data.details as { resource_spec?: Record<string, { label_names?: string[]; labels?: string[] }> }
    ).resource_spec;
    const labelIds = _.uniq(
      Object.values(resourceSpec || {}).flatMap((item) => (item?.label_names?.length ? [] : item?.labels || [])),
    );
    if (labelIds.length > 0) {
      listTag({ ids: labelIds.join(','), limit: labelIds.length, type: 'resource' }).then((res) => {
        labelNameMap.value = Object.fromEntries(res.results.map((item) => [String(item.id), item.value]));
      });
    }
  };

  if (isModify) {
    getInfrasSubzonesByCity().then((list) => {
      subzoneNameMap.value = Object.fromEntries(list.map((item) => [item.bk_sub_zone_id, item.bk_sub_zone]));
    });
    getCloudList().then((list) => {
      cloudNameMap.value = Object.fromEntries(list.map((item) => [item.bk_cloud_id, item.bk_cloud_name]));
    });
    getTicketDetails(
      { id: ticketId },
      {
        cache: 1000,
        permission: 'catch',
      },
    )
      .then((data) => {
        if (!checkEntry(data)) {
          backToDetail();
          return;
        }
        // 与页面回填共用同一份缓存响应，页面会就地改其中的对象（如域名），对比基准要深拷贝一份
        ticketData.value = _.cloneDeep(data);
        fetchTicketNameMaps(data);
      })
      .catch(() => {
        // 拉取失败无法回填也无法对比，回到单据详情页（请求层已提示错误）
        backToDetail();
      });
  }

  const openConfirm = (diffList: DiffItem[], submit: () => Promise<unknown>) =>
    new Promise<void>((resolve) => {
      Object.assign(confirmState, {
        diffList,
        isShow: true,
        isSubmitting: false,
        resolve,
        submit,
      });
    });

  const openUpdated = (operator: string, time: string) => {
    // 确认弹窗与「单据已更新」不同时出现，按取消关闭确认弹窗并结束 openConfirm 返回的 Promise
    confirmState.isShow = false;
    confirmState.resolve?.();
    confirmState.resolve = undefined;
    confirmState.submit = undefined;
    Object.assign(updatedState, {
      isShow: true,
      operator,
      time,
    });
  };

  const getDiffList = (details: unknown) => {
    const data = ticketData.value;
    if (!data) {
      return [];
    }
    const options = getTicketModifyDiffOptions(data.ticket_type);
    return diffDetails(data.details, details, {
      ...options,
      formatters: {
        ...options.formatters,
        // 下列字段单据里只存 id / 代码，名称要靠接口补齐，所以在这里统一登记，覆盖 registry 里只读快照的同名格式
        bk_cloud_id: (value) => {
          const name = cloudNameMap.value[value as number];
          return name ? `${name}[${value}]` : formatValue(value);
        },
        // 非 K8s 类型的快照带 city_name；K8s 类型只有地域代码，按地域列表取名
        city_code: (value, snapshot) =>
          formatValue(snapshot.city_name || regionNameMap.value[value as string] || value),
        'resource_spec.*.labels': (value, snapshot, path) => {
          const labelNames = _.get(snapshot, path.replace(/labels$/, 'label_names')) as string[] | undefined;
          if (labelNames?.length) {
            return formatValue(labelNames);
          }
          return formatValue((value as string[] | undefined)?.map((id) => labelNameMap.value[String(id)] || id));
        },
        'resource_spec.*.location_spec.sub_zone_ids': (value) =>
          formatValue((value as number[] | undefined)?.map((id) => subzoneNameMap.value[id] || id)),
      },
    });
  };

  /**
   * 补充信息对比：交付通知（是否发送、收件人）与单据备注
   * 收件人按集合比较，顺序不同不算改动；不发送时 NotifyRelatedPersons.getValue() 返回空对象，按不发送、无收件人处理
   */
  const getSupplementDiffList = (config: unknown, ticketRemark: string) => {
    const data = ticketData.value;
    if (!data) {
      return [];
    }
    type SendMsgConfig = Partial<TicketModel['config']['send_msg_config']>;
    const getSendInfo = (sendMsgConfig?: SendMsgConfig) => ({
      isSend: Boolean(sendMsgConfig?.is_send),
      receivers: sendMsgConfig?.is_send ? (sendMsgConfig.receiver__username || '').split(',').filter(Boolean) : [],
    });
    const prevSendMsgConfig = data.config?.send_msg_config;
    // 原单据没有交付通知配置时，回填按默认值（发送）处理，对比基准与回填保持一致
    const isPrevDefault = prevSendMsgConfig?.is_send === undefined;
    const prev = isPrevDefault ? { isSend: true, receivers: [] } : getSendInfo(prevSendMsgConfig);
    const next = getSendInfo((config as { send_msg_config?: SendMsgConfig } | undefined)?.send_msg_config);
    const result: DiffItem[] = [];
    if (prev.isSend !== next.isSend) {
      result.push({
        isList: false,
        label: t('发送交付通知'),
        next: next.isSend ? t('是') : t('否'),
        path: 'config.send_msg_config.is_send',
        prev: prev.isSend ? t('是') : t('否'),
      });
    }
    // 原单据没有配置时收件人没有可比的基准（默认收件人由提交时实时计算），不比较收件人
    if (!isPrevDefault && _.xor(prev.receivers, next.receivers).length > 0) {
      result.push({
        isList: true,
        label: t('收件人'),
        next: formatValue(next.receivers),
        path: 'config.send_msg_config.receiver__username',
        prev: formatValue(prev.receivers),
      });
    }
    if ((data.remark || '') !== (ticketRemark || '')) {
      result.push({
        isList: false,
        label: t('备注'),
        next: formatValue(ticketRemark),
        path: 'ticket_remark',
        prev: formatValue(data.remark),
      });
    }
    return result;
  };

  const state: TicketModifyState = {
    backToTicket,
    confirmState,
    confirmTitle: mode ? confirmTitleMap[mode] : '',
    getDiffList,
    getSupplementDiffList,
    isAdjustApply: mode === TicketModifyRecordModel.MODE_ADJUST_APPLY,
    isModify,
    isSelfOnBehalf: computed(
      () => mode === TicketModifyRecordModel.MODE_ON_BEHALF && ticketData.value?.creator === username,
    ),
    mode,
    modifyRemark,
    openConfirm,
    openUpdated,
    resetContent: isModify ? t('重置后本次修改将丢弃，内容回到打开时的状态。') : '',
    submitText: mode ? submitTextMap[mode] : '',
    ticketData,
    updatedState,
    validateRemark: () => Promise.resolve(),
  };

  provide(ticketModifyStateKey, state);

  return state;
};

/**
 * 申请页内的子组件读取改单状态，不在改单工具页时为 null
 */
export const useTicketModifyState = () => {
  const state = inject(ticketModifyStateKey, null);
  return state?.isModify ? state : null;
};
