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

import TaskFlowModel from '@services/model/taskflow/taskflow';

import D3Graph from '@blueking/bkflow.js';

import GraphRender from './graphRender';
import type { GraphNode } from './utils';

interface GraphData {
  locations: GraphNode[],
  lines: any[]
}

export default class GraphCanvas {
  flowInstance: any;
  selector: string;
  tplRender: GraphRender;
  graphData: GraphData;
  expandNodes: string[]; // 展开节点
  flowInfo: TaskFlowModel;

  constructor(selector: string, flowInfo: TaskFlowModel) {
    this.expandNodes = [];
    this.flowInstance = null;
    this.selector = selector;
    this.tplRender = new GraphRender();
    this.graphData = {
      locations: [],
      lines: [],
    };
    this.flowInfo = flowInfo;
    this.renderCanvas();
  }

  renderCanvas() {
    const { flowInfo } = this;
    this.flowInstance = new D3Graph(this.selector, {
      mode: 'readonly',
      nodeTemplateKey: 'tpl',
      canvasPadding: { x: 60, y: 100 },
      background: '#f5f7fb',
      lineConfig: {
        canvasLine: false,
        color: '#C4C6CC',
        type: 'polyline',
        activeColor: '#C4C6CC',
      },
      nodeConfig: [
        { tpl: 'round', width: 48, height: 48, radius: '50%' },
        { tpl: 'ractangle', width: 280, height: 48, radius: '4px' },
      ],
      zoom: {
        scaleExtent: [0.5, 1.5],
        controlPanel: false,
      },
      onNodeRender: (node: any) => this.tplRender.render(node.tpl, [node, flowInfo]),
    });
    this.flowInstance.renderGraph(this.graphData, false);
    this.updateLinePosition();
  }

  setUpdateCallback(callback: () => void) {
    this.flowInstance.updateCallback = callback;
  }

  update(graphData: GraphData) {
    this.graphData = graphData;
    this.flowInstance.clear();
    this.flowInstance.renderGraph(this.graphData, false);
    this.updateLinePosition();
    this.flowInstance?.updateCallback?.();
  }

  on(eventName: string, callback: (node: any, event: any) => void) {
    return this.flowInstance.on(eventName, callback);
  }

  zoomReset() {
    this.flowInstance?.reSet?.();
  }

  zoomIn() {
    this.flowInstance?.zoomIn?.();
  }

  zoomOut() {
    this.flowInstance?.zoomOut?.();
  }

  translate(left: number, top: number) {
    this.flowInstance?.translate?.(left, top);
  }

  destroy() {
    if (!this.flowInstance) return;

    this.flowInstance.clear();
    this.flowInstance = null;
  }

  clear() {
    this.flowInstance?.clear?.();
  }

  /**
   * 自动更新画布连线
   */
  updateLinePosition() {
    // eslint-disable-next-line no-underscore-dangle
    const lineCollectionInstance = this.flowInstance?._lineCollectionInstance;
    if (!lineCollectionInstance) return;

    // 重置 generatePolylineLink 计算方法
    lineCollectionInstance.generatePolylineLink = function (line: any) {
      const chidlOffset = 28;
      const { source, target } = line;
      const { sourceX, sourceY, targetX, targetY } = this.getBezierParams(line);
      const [sOffsetX, sOffsetY] = this.getPolylineOffsetBreakPoints(line, 'source');
      const [tOffsetX, tOffsetY] = this.getPolylineOffsetBreakPoints(line, 'target');
      const pointList = [[sOffsetX, sOffsetY]];

      // 不同层父子节点设置
      if (target.x - source.x === chidlOffset && source.y !== target.y) {
        const offset = 10;
        pointList.push([sOffsetX, targetY + offset]);
        pointList.push([tOffsetX - offset, targetY + offset]);
      } else {
        if (sourceX !== targetX && sourceY !== targetY) {
          let breakPoint = [tOffsetX, sOffsetY];
          if (this.isLineCrossNode([source.x, source.y], [sOffsetX, sOffsetY], breakPoint)
            || this.isLineCrossNode([target.x, target.y], [tOffsetX, tOffsetY], breakPoint)
          ) {
            breakPoint = [sOffsetX, tOffsetY];
          }
          pointList.push([breakPoint[0], breakPoint[1]]);
          pointList.push([tOffsetX, tOffsetY]);
        }
        pointList.push([targetX, targetY]);
      }

      // eslint-disable-next-line no-underscore-dangle
      if (this._linesExtends[this.lineDataKeyFunc(line)]) {
        // eslint-disable-next-line no-underscore-dangle
        Object.assign(this._linesExtends[this.lineDataKeyFunc(line)], { points: [[sourceX, sourceY], ...pointList] });
      } else {
        // eslint-disable-next-line no-underscore-dangle
        this._linesExtends[this.lineDataKeyFunc(line)] = { points: [[sourceX, sourceY], ...pointList] };
      }
      return `M ${sourceX} ${sourceY},${pointList.map(item => `L ${item[0]} ${item[1]}`).join(',')}`;
    };

    lineCollectionInstance.reDrawLins(this.graphData.lines);
  }
}
