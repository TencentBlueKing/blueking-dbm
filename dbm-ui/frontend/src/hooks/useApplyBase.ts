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
import { useI18n } from 'vue-i18n';

import TicketModifyRecordModel from '@services/model/ticket/modify-record';
import TicketModel from '@services/model/ticket/ticket';
import { createAppAbbr } from '@services/source/cmdb';
import { getTicketStatus, modifyTicket } from '@services/source/ticket';
import type { BizItem } from '@services/types';

import { useCreateTicket } from '@hooks';

import { type RequestErrorBody, TICKET_MODIFY_ERROR_CODE } from '@views/ticket-center/common/ticket-modify/constants';

import { getBusinessHref, messageError, messageWarn } from '@utils';

import { useTicketModify } from './useTicketModify';

/**
 * 申请服务基础信息设置
 */
export const useApplyBase = () => {
  const { t } = useI18n();
  const route = useRoute();
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
   * 取消申请；改单模式下返回单据详情
   */
  function handleCancel() {
    if (modifyState.isModify) {
      router.push({
        name: 'ticketDetail',
        params: {
          ticketId: Number(route.query.ticketId),
        },
      });
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
   * 改单提交被拦截：身份、状态、内容三类提示可区分，留在工具页
   * 其余错误码未接管，已由请求层提示
   */
  function handleModifyError(error: unknown, ticketId: number) {
    const code = (error as RequestErrorBody | undefined)?.code;
    if (code === TICKET_MODIFY_ERROR_CODE.NO_PERMISSION) {
      messageError(t('您没有该单据的改单权限'));
      return;
    }
    if (code === TICKET_MODIFY_ERROR_CODE.CONTENT_CHANGED) {
      messageError(t('单据内容已被他人修改'));
      return;
    }
    if (code === TICKET_MODIFY_ERROR_CODE.STATUS_UNSUPPORTED || code === TICKET_MODIFY_ERROR_CODE.APPROVED) {
      getTicketStatus({
        ticket_ids: `${ticketId}`,
      }).then((data) => {
        const status = data[ticketId] as keyof typeof TicketModel.statusTextMap;
        messageError(t('单据状态已变更为{status}', { status: TicketModel.statusTextMap[status] || status }));
      });
    }
  }

  /**
   * 改单提交：与进入时的单据内容对比，确认后调用改单接口，成功后回到单据详情
   */
  function handleModifyTicket(details: unknown) {
    const ticketData = modifyState.ticketData.value;
    const { mode } = modifyState;
    if (!ticketData || !mode) {
      baseState.isSubmitting = false;
      messageError(t('单据信息加载失败，请刷新后重试'));
      return;
    }
    modifyState
      .validateRemark()
      .then(() => {
        const diffList = modifyState.getDiffList(details);
        if (diffList.length < 1) {
          messageWarn(t('没有改动'));
          return;
        }
        return modifyState.openConfirm(diffList).then((isConfirmed) => ({ diffList, isConfirmed }));
      })
      .then((result) => {
        if (!result?.isConfirmed) {
          return;
        }
        const { diffList } = result;
        return modifyTicket(
          {
            change_count: diffList.length,
            details,
            id: ticketData.id,
            mode,
            remark: mode === TicketModifyRecordModel.MODE_RE_EDIT ? '' : modifyState.modifyRemark.value,
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
            router.replace({
              name: 'ticketDetail',
              params: {
                ticketId: ticketData.id,
              },
            });
          })
          .catch((error) => handleModifyError(error, ticketData.id));
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
      handleModifyTicket(params.details);
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
        const { href } = router.resolve({
          name: 'bizTicketManage',
        });
        window.open(getBusinessHref(href, formdata.bk_biz_id), '_blank');
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
