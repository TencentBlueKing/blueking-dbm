import { type ResourceTopo } from '@services/types';

import { type Group, Rect as GRect, Text as GText } from '@antv/g';
import { type BaseNodeStyleProps, type BaseStyleProps, Rect } from '@antv/g6';

type Node = { id: string; name: string; type: string } & ResourceTopo['groups'][number];
type AttributesType = Required<BaseNodeStyleProps>;

function getTextWidth(text: string, fontStyle = '12px Arial') {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;
  ctx.font = fontStyle;
  return ctx.measureText(text).width;
}

export class TopoNode extends Rect {
  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  drawContentShape(attributes: AttributesType, container: Group) {
    const [width, height] = this.getSize(attributes);
    const style = {
      cursor: 'pointer' as BaseStyleProps['cursor'],
      fill: '#63656e',
      fontFamily: 'Arial',
      fontSize: 12,
      text: this.data.name,
      x: -width / 2 + 46,
      y: -height / 2 + 23,
    };

    this.upsert('content', GText, style, container);
  }

  drawGroupShape(attributes: AttributesType, container: Group) {
    const [width, height] = this.getSize(attributes);
    const startWidth = -width / 2;
    const startHeight = -height / 2;
    const iconWraperStyle = {
      fill: '#4bc7ad',
      height: 24,
      text: this.data.name,
      width: 24,
      x: startWidth + 12,
      y: startHeight + 12,
    };
    this.upsert('groupIconWraper', GRect, iconWraperStyle, container);
    const iconText = this.data.name.substring(0, 1).toUpperCase();
    const iconTextWidth = getTextWidth(iconText);
    const iconWidthOffset =
      iconTextWidth < 12 ? (iconTextWidth < 9 ? iconTextWidth + 11 : iconTextWidth + 8) : iconTextWidth + 5;
    const commonStyle = {
      fontFamily: 'Arial',
      fontSize: 12,
      fontWeight: 700,
      zIndex: 1,
    };
    const iconTextStyle = {
      fill: '#fff',
      text: iconText,
      x: startWidth + iconWidthOffset,
      y: startHeight + 32,
      ...commonStyle,
    };
    this.upsert('groupIconText', GText, iconTextStyle, container);
    const titleTextStyle = {
      fill: '#63656e',
      text: this.data.name,
      x: startWidth + 46,
      y: startHeight + 32,
      ...commonStyle,
    };
    this.upsert('groupTitleText', GText, titleTextStyle, container);
  }

  renderNode(attributes: AttributesType, container: Group) {
    if (this.data.type === 'group') {
      this.drawGroupShape(attributes, container);
      return;
    }

    this.drawContentShape(attributes, container);
  }

  // eslint-disable-next-line perfectionist/sort-classes
  render(attributes = this.parsedAttributes as AttributesType, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }
}
