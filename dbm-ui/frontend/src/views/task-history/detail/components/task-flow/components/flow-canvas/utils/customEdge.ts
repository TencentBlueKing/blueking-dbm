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

import { FlowTypes } from '@services/source/taskflow';

import { forkGatewayTypes } from '@views/task-history/detail/utils';

import { type Group } from '@antv/g';
import { type Point, Polyline } from '@antv/g6';

import { trunkGap } from './layout';

export default class CustomEdge extends Polyline {
  startEndPoint: [Point, Point] = [
    [0, 0],
    [0, 0],
  ];
  /**
   * 子流程节点连进它自己展开出来的内容。这条边从节点下方的引出点垂直落到子层，
   * 端点和折线走法都和同层的普通连线不一样
   */
  get isEnterSubProcess() {
    return this.isSourceSubProcess && this.sourceNodeData.level < this.targetNodeData.level;
  }

  /**
   * 边属于一组扇出或汇聚。同组的边共用一条竖直干线，才值得多绕两折；
   * 单独一条连线没有干线可并，多绕只是累赘
   */
  get isFanEdge() {
    return this.isForkEdge || this.targetNodeData.type === FlowTypes.ConvergeGateway;
  }

  /** 源是扇出网关：这组边的干线在网关右侧，汇聚则相反，干线在网关左侧 */
  get isForkEdge() {
    return forkGatewayTypes.includes(this.sourceNodeData.type);
  }

  get isSourceNodeAboveTargetNode() {
    return this.sourceNodeData.style.y < this.targetNodeData.style.y;
  }
  get isSourceSubProcess() {
    return this.sourceNodeData.type === 'SubProcess';
  }

  get sourceNodeData() {
    return (this.sourceNode as any).data;
  }

  get targetNodeData() {
    return (this.targetNode as any).data;
  }

  drawCircleToStartNode(container: Group) {
    if (this.isEnterSubProcess) {
      this.upsert(
        'subprocessStartCricle',
        'circle',
        {
          cx: this.startEndPoint[0][0],
          cy: this.startEndPoint[0][1],
          fill: '#fff',
          r: 3,
          stroke: '#C4C6CC',
        },
        container,
      );
    }
  }

  protected getEndpoints(attributes: any, optimize?: boolean, controlPoints?: Point[] | (() => Point[])) {
    const startEndPoint = super.getEndpoints(attributes, optimize, controlPoints);
    // 只有进入子流程的入口边需要把端点挪到引出点上，同层的普通连线用端口原位，
    // 挪了会让线和节点右边缘之间空出一截
    if (this.isEnterSubProcess) {
      // 引出点对齐源节点左侧状态色块的水平中心（见 normalNode 的 mainStatusBackground），
      // 竖线才是从色块正下方落下来的
      const { style } = this.sourceNodeData;
      const drawOutX = style.x - style.width / 2 + 38;
      if (
        startEndPoint[0][0] > this.targetNodeData.style.x + this.targetNodeData.style.width ||
        (this.isSourceNodeAboveTargetNode &&
          startEndPoint[0][0] < startEndPoint[1][0] &&
          this.targetNodeData.type === 'ServiceActivity')
      ) {
        startEndPoint[0][0] = drawOutX;
        // 目标这时取到的是右端口，退一个节点宽回到左端口
        startEndPoint[1][0] = startEndPoint[1][0] - this.targetNodeData.style.width;
      } else if (this.isSourceNodeAboveTargetNode) {
        startEndPoint[0][0] = drawOutX;
      }
      // 端口在节点的纵向中心，而边画在节点之上（见 flowGraph 的 edge.style.zIndex），
      // 起点留在端口上竖线会从卡片正中穿出来，这里落到卡片下边缘外的引出点上
      startEndPoint[0][1] = style.y + style.height / 2 + 3;
    }
    // 子流程节点的包围盒左侧留了 14px 空档，放横跨在卡片左边框上的展开收起图标（见 normalNode 的
    // drawCollapseShape）。左端口落在空档外沿，箭头会停在图标左边空出一段，补进半个空档顶到图标上
    const { style: targetStyle } = this.targetNodeData;
    if (this.targetNodeData.pipeline && startEndPoint[1][0] < targetStyle.x) {
      startEndPoint[1][0] = targetStyle.x - targetStyle.width / 2 + 7;
    }
    this.startEndPoint = startEndPoint;
    return startEndPoint;
  }

  protected getKeyPath(attributes: any) {
    const keyPathStyle = super.getKeyPath(attributes)!;
    // 这两条边没有配 controlPoints，基类给的就是「起点 + 终点」两条指令
    const [, startX, startY] = keyPathStyle[0] as ['M', number, number];
    const [, endX, endY] = keyPathStyle[1] as ['L', number, number];
    if (startY === endY) {
      return keyPathStyle;
    }
    // 单条连线一个拐点就够：在起点的 x 上竖直走到目标高度，再水平进端口。
    // 入口边也走这条，它的竖线必须压在节点下方那个引出点上，挪开就和圆点断开了
    if (this.isEnterSubProcess || !this.isFanEdge) {
      keyPathStyle.splice(1, 0, ['L', startX, endY]);
      return keyPathStyle;
    }
    // 扇出与汇聚的边走「水平引出 → 干线竖直 → 水平进端口」三段。干线贴着网关那一侧，
    // 同组的边落在同一个 x 上会重合成一条，两端各留一段可见的引出线；
    // 最后一段恒为水平，箭头才是平着进端口的。
    // 贴网关而不是取起终点中点：分支列被展开的子内容撑宽时，中点会跟着落进内容里，
    // 而布局保证了网关这一侧留有 trunkGap 的净空
    const trunkX = this.isForkEdge ? startX + trunkGap : endX - trunkGap;
    keyPathStyle.splice(1, 0, ['L', trunkX, startY], ['L', trunkX, endY]);
    return keyPathStyle;
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering, perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.drawCircleToStartNode(container);
  }
}
