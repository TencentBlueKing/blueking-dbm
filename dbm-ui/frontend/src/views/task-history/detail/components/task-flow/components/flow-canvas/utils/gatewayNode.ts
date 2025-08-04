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

  drawBackground(attributes: any, container: Group) {
    const backgroundShapeStyle = {
      fill: '#fff',
      height: 48,
      radius: 24,
      shadowBlur: 4,
      shadowColor: attributes.nodeBackgroundshadowColor,
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      width: 48,
      x: -24,
      y: -24,
      zIndex: 0,
    };
    this.upsert('backgroundShape', GRect, backgroundShapeStyle, container);
    const iconWraperShapeStyle = {
      fill: '#F0F1F5',
      height: 40,
      radius: 20,
      width: 40,
      x: -20,
      y: -20,
      zIndex: 0,
    };
    this.upsert('iconWraperShape', GRect, iconWraperShapeStyle, container);
  }

  drawFocusBackgroundShape(attributes: any, container: Group) {
    const [width, height] = this.getSize(attributes);
    const focusBackgroundStyle = {
      fill: '#E1ECFF',
      height: height + 16,
      radius: 2,
      stroke: '#3A84FF',
      visibility: attributes.focusNodeVisibility,
      width: width + 16,
      x: -width / 2 - 8,
      y: -height / 2 - 8,
    };
    this.upsert('focusBackground', GRect, focusBackgroundStyle, container);
  }

  // 基类方法覆盖
  drawIconShape(attributes: any, container: Group) {
    const [width, height] = this.getSize(attributes);
    const gatewayIconStyle = {
      height: 25,
      src: iconMap[this.data.type as keyof typeof iconMap],
      width: 25,
      x: -width / 2 + 11.5,
      y: -height / 2 + 11.5,
      zIndex: 1,
    };
    this.upsert('gatewayIcon', GImage, gatewayIconStyle, container);
  }

  renderNode(attributes: any, container: Group) {
    this.drawFocusBackgroundShape(attributes, container);
    this.drawBackground(attributes, container);
  }

  // protected getKeyStyle(attributes: any) {
  //   const keyStyle = super.getKeyStyle(attributes);
  //   keyStyle.ports = [{ placement: 'left' }, { placement: 'right' }];
  //   return keyStyle;
  // }

  // eslint-disable-next-line perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }
}
