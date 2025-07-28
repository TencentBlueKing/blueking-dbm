import { type Group } from '@antv/g';
import { CubicHorizontal, type Point } from '@antv/g6';

export default class CustomEdge extends CubicHorizontal {
  get isSourceSubProcess() {
    return (this.sourceNode as any).data.type === 'SubProcess';
  }

  get isStartNodeOfSubProcess() {
    return !!(this.targetNode as any).data.isStartNodeOfSubProcess;
  }

  protected getEndpoints(
    attributes: any,
    optimize?: boolean,
    controlPoints?: Point[] | (() => Point[]),
  ): [Point, Point] {
    const startEndPoint = super.getEndpoints(attributes, optimize, controlPoints);
    if (this.isSourceSubProcess && this.isStartNodeOfSubProcess) {
      startEndPoint[0][0] = startEndPoint[0][0] - 125;
      startEndPoint[0][1] = startEndPoint[0][1] + 28;
    }
    return startEndPoint;
  }

  // eslint-disable-next-line perfectionist/sort-classes, @typescript-eslint/member-ordering
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
  }
}
