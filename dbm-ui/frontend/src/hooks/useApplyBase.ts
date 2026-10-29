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

import { Message } from 'bkui-vue';
import InfoBox from 'bkui-vue/lib/info-box';
import _ from 'lodash';
import { useI18n } from 'vue-i18n';

import TicketModifyRecordModel from '@services/model/ticket/modify-record';
import { createAppAbbr } from '@services/source/cmdb';
import { getTicketDetails, getTicketModifyRecords, modifyTicket } from '@services/source/ticket';
import type { BizItem } from '@services/types';

import { useCreateTicket } from '@hooks';

import { type RequestErrorBody, TICKET_MODIFY_ERROR_CODE } from '@views/ticket-center/common/ticket-modify/constants';

import { getBusinessHref, messageError, messageWarn, utcDisplayTime } from '@utils';

import { useTicketModify } from './useTicketModify';

/**
 * 申请服务基础信息设置
 */
export const useApplyBase = () => {
  const { t } = useI18n();
  const router = useRouter();

  const { run: createTicketRun } = useCreateTicket(undefined, {
    isToolbox: false,
    successMessage: false,
  });
  const modifyState = useTicketModify();

  // 业务相关状态
  const bizState = reactive({
    englistName: '',
    hasEnglishName: false,
    info: {} as BizItem,
  });
  const baseState = reactive({
    isSubmitting: false,
  });
  // 上一次同步的业务，用于区分「页面自动带出」与「用户切换业务」
  let prevBizId: number | undefined;

  /**
   * 取消申请；改单模式下回到单据详情
   */
  function handleCancel() {
    if (modifyState.isModify) {
      modifyState.backToTicket();
      return;
    }
    router.push({ name: 'serviceApply' });
  }

  /**
   * 同步当前业务；仅在用户切换业务时返回 true（首次自动带出不算变更，不要清空规格 / IP）
   */
  function applyBizInfo(info: BizItem) {
    const bizChanged = prevBizId !== undefined && prevBizId !== info.bk_biz_id;
    prevBizId = info.bk_biz_id;
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
    return bizChanged;
  }

  /**
   * 创建业务英文缩写
   */
  function handleCreateAppAbbr(formdata: any) {
    const appAbbr = formdata.details.db_app_abbr;
    const bizName = bizState.info.display_name || bizState.info.name || '';
    InfoBox({
      content: t('业务Codexx将被保存到业务xx且保存后不允许修改', [appAbbr, bizName]),
      onCancel: () => {
        baseState.isSubmitting = false;
      },
      onConfirm: () => {
        baseState.isSubmitting = true;
        createAppAbbr({
          db_app_abbr: appAbbr,
          id: formdata.bk_biz_id as number,
        })
          .then(() => {
            bizState.hasEnglishName = true;
            bizState.info.english_name = appAbbr;
            handleCreateTicket(formdata);
          })
          .catch(() => {
            baseState.isSubmitting = false;
          });
        return true;
      },
      title: t('确认创建业务Code'),
    });
  }

  /**
   * 回到业务单据列表并打开该单据详情侧栏（列表页按路由 ticketId 自动打开）；replace 避免返回到已提交的表单
   * 业务路由前缀在页面初始化时按当前业务固定，单据不属于当前业务时只能整页跳转到单据所属业务
   */
  function openTicketInList(ticketId: number, bizId: number) {
    const ticketRoute = {
      name: 'bizTicketManage',
      params: {
        ticketId,
      },
    };
    if (bizId !== window.PROJECT_CONFIG.BIZ_ID) {
      window.location.replace(getBusinessHref(router.resolve(ticketRoute).href, bizId));
      return;
    }
    router.replace(ticketRoute);
  }

  /**
   * 改单提交被拦截：
   * 内容已修改、状态不支持修改、已被审批，都是单据在打开后被他人更新，统一弹「单据已更新」只能返回单据；
   * 无权修改提示后返回单据详情；缺少版本号是页面信息不完整，提示刷新
   * 其余错误码未接管，已由请求层提示
   */
  function handleModifyError(error: unknown, ticketId: number) {
    const code = (error as RequestErrorBody | undefined)?.code;
    if (code === TICKET_MODIFY_ERROR_CODE.NO_PERMISSION) {
      messageError(t('无权修改该单据'));
      window.changeConfirm = false;
      modifyState.backToTicket();
      return;
    }
    if (code === TICKET_MODIFY_ERROR_CODE.MISSING_VERSION) {
      messageError(t('页面信息不完整，请刷新页面后重试'));
      return;
    }
    // 内容被改时更新人取最近一条改单记录；状态变化（审批、撤销等）不产生改单记录，取单据的最后更新人
    if (code === TICKET_MODIFY_ERROR_CODE.CONTENT_CHANGED) {
      getTicketModifyRecords({ id: ticketId }).then((recordList) => {
        const latestRecord = _.last(recordList);
        modifyState.openUpdated(latestRecord?.operator || '', latestRecord?.createAtDisplay || '');
      });
      return;
    }
    if (code === TICKET_MODIFY_ERROR_CODE.STATUS_UNSUPPORTED || code === TICKET_MODIFY_ERROR_CODE.APPROVED) {
      getTicketDetails({ id: ticketId }).then((data) => {
        modifyState.openUpdated(data.updater, utcDisplayTime(data.update_at));
      });
    }
  }

  /**
   * 改单提交：与进入时的单据内容对比，确认后调用改单接口，成功后回到业务单据列表并打开该单据详情
   * 确认弹窗展示的变更项原样作为 change_details 提交，详情页的变更对比直接展示它
   * 重新编辑、代为修改提交补充信息（交付通知 config、单据备注 ticket_remark）；调整申请只改资源条件，补充信息只读，不提交
   */
  function handleModifyTicket(details: unknown, config: unknown, ticketRemark: string) {
    const ticketData = modifyState.ticketData.value;
    const { mode } = modifyState;
    if (!ticketData || !mode) {
      baseState.isSubmitting = false;
      messageError(t('单据信息加载失败，请刷新后重试'));
      return;
    }
    const isReEdit = mode === TicketModifyRecordModel.MODE_RE_EDIT;
    const isSubmitSupplement = !modifyState.isAdjustApply;
    modifyState
      .validateRemark()
      .then(() => {
        const diffList = [
          ...modifyState.getDiffList(details),
          ...(isSubmitSupplement ? modifyState.getSupplementDiffList(config, ticketRemark) : []),
        ];
        if (diffList.length < 1) {
          messageWarn(t('没有改动'));
          return;
        }
        // 接口调用交给确认弹窗的提交按钮执行：按钮 loading 到接口返回，成功后跳转，失败弹窗保持打开
        const submit = () =>
          modifyTicket(
            {
              change_count: diffList.length,
              change_details: diffList,
              ...(isSubmitSupplement ? { config, ticket_remark: ticketRemark } : {}),
              details,
              id: ticketData.id,
              mode,
              remark: isReEdit ? '' : modifyState.modifyRemark.value,
              // 直接提交进入时单据详情返回的版本；详情未返回版本表示还没改过单，传 1
              version: ticketData.version ?? 1,
            },
            {
              catchErrorCodes: Object.values(TICKET_MODIFY_ERROR_CODE),
            },
          )
            .then(() => {
              Message({
                message: t('提交成功'),
                theme: 'success',
              });
              window.changeConfirm = false;
              openTicketInList(ticketData.id, ticketData.bk_biz_id);
            })
            .catch((error) => {
              handleModifyError(error, ticketData.id);
              return Promise.reject(error);
            });
        return modifyState.openConfirm(diffList, submit);
      })
      .finally(() => {
        baseState.isSubmitting = false;
      });
  }

  function handleCreateTicket(formdata: any) {
    const params = { ...formdata };
    delete params.sub_zone_ids;
    delete params.sub_zone_names;
    delete params.city_name;

    if (modifyState.isModify) {
      handleModifyTicket(params.details, params.config, params.remark ?? '');
      return;
    }

    createTicketRun(params)
      .then((ticketId) => {
        if (!ticketId) {
          return;
        }
        Message({
          message: t('申请成功'),
          theme: 'success',
        });
        // 与改单提交一致，回到业务单据列表并打开新单据详情
        openTicketInList(ticketId, params.bk_biz_id ?? window.PROJECT_CONFIG.BIZ_ID);
      })
      .finally(() => {
        baseState.isSubmitting = false;
      });
  }

  return {
    applyBizInfo,
    baseState,
    bizState,
    handleCancel,
    handleCreateAppAbbr,
    handleCreateTicket,
    modifyState,
  };
};
