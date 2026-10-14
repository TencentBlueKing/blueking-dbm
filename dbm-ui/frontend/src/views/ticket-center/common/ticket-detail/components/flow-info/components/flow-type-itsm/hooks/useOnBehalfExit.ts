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
import FlowMode from '@services/model/ticket/flow';
import TicketModifyRecordModel from '@services/model/ticket/modify-record';

/**
 * 「单据审批」步骤是否以代为修改结束
 * 审批人提交代为修改即结束本步骤（后端可能把该步骤置为完成、终止或跳过），拒绝、免审批不会产生代为修改记录
 */
export default function useOnBehalfExit(
  getFlowData: () => FlowMode<unknown, any>,
  getModifyRecords: () => TicketModifyRecordModel[],
) {
  const onBehalfRecord = computed(() =>
    getModifyRecords().find(
      (item) => item.flow_id === getFlowData().id && item.mode === TicketModifyRecordModel.MODE_ON_BEHALF,
    ),
  );

  // 审批待办的处理人集合，展示协助人时去掉实际处理人
  const itsmOperators = computed(
    () => getFlowData().todos.find((item) => item.type === FlowMode.TODO_TYPE_ITSM)?.operators || [],
  );

  return {
    itsmOperators,
    onBehalfRecord,
  };
}
