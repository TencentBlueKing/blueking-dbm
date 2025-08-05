import { type Group } from '@antv/g';
import { type Point, Polyline } from '@antv/g6';

export default class CustomEdge extends Polyline {
  startEndPoint: [Point, Point] = [
    [0, 0],
    [0, 0],
  ];
  get isSourceNodeBelowTargetNode() {
    return this.sourceNodeData.style.y < this.targetNodeData.style.y;
  }
  get isSourceSubProcess() {
    return this.sourceNodeData.type === 'SubProcess';
  }
  get isStartNodeOfSubProcess() {
    return !!this.targetNodeData.isStartNodeOfSubProcess;
  }

  get sourceNodeData() {
    return (this.sourceNode as any).data;
  }

  get targetNodeData() {
    return (this.targetNode as any).data;
  }

  drawCircleToStartNode(container: Group) {
    if (this.isSourceSubProcess && this.sourceNodeData.level < this.targetNodeData.level) {
      this.upsert(
        'subprocessStartCricle',
        'circle',
        {
          cx: this.startEndPoint[0][0],
          cy: this.startEndPoint[0][1] + 31,
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
    if (this.isSourceSubProcess) {
      if (
        startEndPoint[0][0] > this.targetNodeData.style.x + this.targetNodeData.style.width ||
        (this.isSourceNodeBelowTargetNode &&
          startEndPoint[0][0] < startEndPoint[1][0] &&
          this.targetNodeData.type === 'ServiceActivity')
      ) {
        // 上一级右边连到下一级网关节点起点的右边
        startEndPoint[0][0] = startEndPoint[0][0] - 212;
        startEndPoint[1][0] = startEndPoint[1][0] - this.targetNodeData.style.width;
      } else if (this.isSourceNodeBelowTargetNode) {
        // 上一级左边有点偏左了
        startEndPoint[0][0] = startEndPoint[0][0] + 40;
      }
    }
    this.startEndPoint = startEndPoint;
    return startEndPoint;
  }

  protected getKeyPath(attributes: any) {
    const keyPathStyle = super.getKeyPath(attributes);
    // 垂直边线校正
    if (this.sourceNodeData.style.y < this.targetNodeData.style.y) {
      keyPathStyle.splice(1, 0, ['L', keyPathStyle[0][1], keyPathStyle[1][2]] as any);
    } else if (this.sourceNodeData.style.y > this.targetNodeData.style.y) {
      keyPathStyle.splice(1, 0, ['L', keyPathStyle[1][1], keyPathStyle[0][2]] as any);
    }
    return keyPathStyle;
  }

  // eslint-disable-next-line @typescript-eslint/member-ordering, perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.drawCircleToStartNode(container);
  }
}
