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
import { useI18n } from 'vue-i18n';

import { createAppAbbr, createTicket } from '@services/ticket';
import type { BizItem } from '@services/types/common';

import { useInfo } from '@hooks';

import { useMainViewStore } from '@stores';

import {
  serviceTicketTypes,
  type ServiceTicketTypeStrings,
} from '@common/const';

/**
 * 申请服务基础信息设置
 */
export const useApplyBase = () => {
  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const mainViewStore = useMainViewStore();

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
   * 设置导航名称
   */
  watch(() => route.params.type, (value, old) => {
    if (value && value !== old) {
      const info = serviceTicketTypes[value as ServiceTicketTypeStrings];
      mainViewStore.breadCrumbsTitle = info ? t('申请xx', [info.name]) : t('申请服务');
    }
  }, { immediate: true });


  /**
   * 取消申请
   */
  function handleCancel() {
    router.push({ name: 'SelfServiceApply' });
  }

  /**
   * 创建业务英文缩写
   */
  function handleCreateAppAbbr(formdata: any) {
    const appAbbr = formdata.details.db_app_abbr;
    useInfo({
      title: t('确认创建业务Code'),
      content: t('业务Codexx将被保存到业务xx且保存后不允许修改', [appAbbr, bizState.info.display_name]),
      onConfirm: () => {
        baseState.isSubmitting = true;
        createAppAbbr(formdata.bk_biz_id as number, { db_app_abbr: appAbbr })
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
      onCancel: () => {
        baseState.isSubmitting = false;
      },
    });
  }

  function handleCreateTicket(formdata: any) {
    createTicket(formdata)
      .then(() => {
        Message({
          message: t('申请成功'),
          theme: 'success',
        });
        window.changeConfirm = false;
        router.push({ name: 'SelfServiceMyTickets' });
      })
      .finally(() => {
        baseState.isSubmitting = false;
      });
  }

  return {
    baseState,
    bizState,
    handleCancel,
    handleCreateAppAbbr,
    handleCreateTicket,
  };
};
