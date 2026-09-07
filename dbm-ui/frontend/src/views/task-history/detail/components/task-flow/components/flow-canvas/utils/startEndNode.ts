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

import { t } from '@locales/index';

import { Circle as GCircle, type Group, Rect as GRect, Text as GText } from '@antv/g';
import { Rect } from '@antv/g6';

import { type Node } from './layout';

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
    if (!width || !height) {
      return;
    }

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
    const text = this.isStartNode ? t('始') : t('终');
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

  // eslint-disable-next-line perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }
}
