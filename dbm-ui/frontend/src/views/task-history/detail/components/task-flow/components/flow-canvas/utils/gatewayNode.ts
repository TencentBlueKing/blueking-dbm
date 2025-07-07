import { FlowTypes } from '@services/source/taskflow';

import BranchGatewayImage from '@images/branch-gateway.png';
import ConvergeGatewayImage from '@images/converge-gateway.png';
import ParallelGatewayImage from '@images/parallel-gateway.png';

import { type Group, Image as GImage, Rect as GRect } from '@antv/g';
import { Rect } from '@antv/g6';

import { type Node } from './calculate';

const iconMap = {
  [FlowTypes.ConditionalParallelGateway]: BranchGatewayImage,
  [FlowTypes.ConvergeGateway]: ConvergeGatewayImage,
  [FlowTypes.ParallelGateway]: ParallelGatewayImage,
};

export class GatewayNode extends Rect {
  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  // 基类方法覆盖
  drawIconShape(attributes: any, container: Group) {
    const [width, height] = this.getSize(attributes);
    const gatewayIconStyle = {
      height: 30,
      src: iconMap[this.data.type as keyof typeof iconMap],
      width: 30,
      x: -width / 2 + 8,
      y: -height / 2 + 8,
      zIndex: 1,
    };

    this.upsert('gatewayIcon', GImage, gatewayIconStyle, container);
  }

  renderBackground(_: any, container: Group) {
    const backgroundShapeStyle = {
      fill: '#fff',
      height: 48,
      radius: 24,
      shadowBlur: 4,
      shadowColor: '#1919290d',
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      width: 48,
      x: -24,
      y: -24,
      zIndex: 0,
    };
    this.upsert('backgroundShape', GRect, backgroundShapeStyle, container);
  }

  // eslint-disable-next-line perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderBackground(attributes, container);
  }
}
