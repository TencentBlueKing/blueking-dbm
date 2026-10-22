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
 * 并入主摘要展示的改单记录：步骤内只有一条记录，且这条记录就是结束该步骤的处理时，
 * 变更对比与修改原因挂在主摘要（{处理人} 已处理（{出口}））上，不再单独渲染记录块。
 * 会结束步骤的只有两种：代为修改结束「单据审批」，重新提交结束「修改内容确认」；
 * 待审批下的重新提交、待补货下的调整申请是步骤内修改，不结束步骤，照常走记录块
 */
export const getSummaryRecord = (
  flowData: Pick<FlowMode<unknown, any>, 'id' | 'todos'>,
  modifyRecords: TicketModifyRecordModel[],
) => {
  const recordList = modifyRecords.filter((item) => item.flow_id === flowData.id);
  if (recordList.length !== 1) {
    return undefined;
  }
  const [record] = recordList;
  if (record.mode === TicketModifyRecordModel.MODE_ON_BEHALF) {
    return record;
  }
  const isConfirmModifyFlow = flowData.todos.some((item) => item.type === FlowMode.TODO_TYPE_CONFIRM_MODIFY);
  if (record.mode === TicketModifyRecordModel.MODE_RE_EDIT && isConfirmModifyFlow) {
    return record;
  }
  return undefined;
};
