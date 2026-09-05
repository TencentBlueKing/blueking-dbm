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

import { createAppAbbr } from '@services/source/cmdb';
import { createTicket } from '@services/source/ticket';
import type { BizItem } from '@services/types';

import { getBusinessHref } from '@utils';

/**
 * 申请服务基础信息设置
 */
export const useApplyBase = () => {
  const { t } = useI18n();
  const router = useRouter();

  // 业务相关状态
  const bizState = reactive({
    englistName: '',
    hasEnglishName: false,
    info: {} as BizItem,
  });
  const baseState = reactive({
    isSubmitting: false,
  });

  /**
   * 取消申请
   */
  function handleCancel() {
    router.push({ name: 'serviceApply' });
  }

  /**
   * 同步当前业务；仅在已有业务且 bk_biz_id 变化时返回 true（自动带出同一业务时不要清空规格 / IP）
   */
  function applyBizInfo(info: BizItem) {
    const prevId = bizState.info.bk_biz_id;
    const bizChanged = prevId !== undefined && prevId !== info.bk_biz_id;
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

  function handleCreateTicket(formdata: any) {
    const params = { ...formdata };
    delete params.sub_zone_ids;
    delete params.sub_zone_names;
    delete params.city_name;

    createTicket(params)
      .then((data) => {
        Message({
          message: t('申请成功'),
          theme: 'success',
        });
        window.changeConfirm = false;
        const { href } = router.resolve({
          name: 'bizTicketManage',
        });
        window.open(getBusinessHref(href, data.bk_biz_id), '_blank');
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
  };
};
