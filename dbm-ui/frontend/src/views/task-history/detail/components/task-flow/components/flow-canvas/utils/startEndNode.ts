import { FlowTypes } from '@services/source/taskflow';

import { Circle as GCircle, type Group, Rect as GRect, Text as GText } from '@antv/g';
import { Rect } from '@antv/g6';

import { type Node } from './calculate';

export class StartEndNode extends Rect {
  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  get isStartNode() {
    return this.data.type === FlowTypes.EmptyStartEvent;
  }

  drawBackgroundShape(attributes: any, container: Group) {
    const backgroundShapeStyle = {
      fill: '#fff',
      r: 24,
      shadowBlur: 4,
      shadowColor: attributes.nodeBackgroundshadowColor,
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      zIndex: 1,
    };
    this.upsert('backgroundShape', GCircle, backgroundShapeStyle, container);
    const iconWraperShapeStyle = {
      fill: this.isStartNode ? '#3DC2A6' : '#C4C6CC',
      r: 18,
      zIndex: 1,
    };
    this.upsert('iconWraperShape', GCircle, iconWraperShapeStyle, container);
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

  drawTitleShape(_: any, container: Group) {
    const text = this.isStartNode ? '始' : '终';
    const titleShapeStyle = {
      fill: '#FFF',
      fontFamily: 'MicrosoftYaHei',
      fontSize: 12,
      fontWeight: 700,
      text,
      x: -6,
      y: 8,
      zIndex: 1,
    };
    this.upsert('titleShape', GText, titleShapeStyle, container);
  }

  renderNode(attributes: any, container: Group) {
    this.drawFocusBackgroundShape(attributes, container);
    this.drawBackgroundShape(attributes, container);
    this.drawTitleShape(attributes, container);
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
