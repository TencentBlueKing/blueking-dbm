import { FlowTypes } from '@services/source/taskflow';

import EndImage from '@images/end.png';
import StartImage from '@images/start.png';

import { Circle as GCircle, type Group, Image as GImage } from '@antv/g';
import { Rect } from '@antv/g6';

import { type Node } from './calculate';

export class StartEndNode extends Rect {
  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  renderNode(attributes: any, container: Group) {
    const { type } = this.data;
    const [height, width] = this.getSize(attributes);
    const startEndWraperStyle = {
      fill: '#fff',
      r: 24,
      shadowBlur: 4,
      shadowColor: '#1919290d',
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      zIndex: 1,
    };
    this.upsert('startEndWraper', GCircle, startEndWraperStyle, container);
    const startEndImageStyle = {
      height: 36,
      src: type === FlowTypes.EmptyStartEvent ? StartImage : EndImage,
      width: 36,
      x: -width / 2 + 6,
      y: -height / 2 + 6,
      zIndex: 2,
    };
    this.upsert('startEndImage', GImage, startEndImageStyle, container);
  }

  // eslint-disable-next-line perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }
}
