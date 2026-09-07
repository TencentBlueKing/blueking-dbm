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

import _ from 'lodash';

import { getNodeDisplayStatus, NODE_STATUS_META } from '@views/task-history/detail/utils';

import { encodeRegexp, getCostTimeDisplay } from '@utils';

import { t } from '@locales/index';

import AiBluekingImage from '@images/ai-blueking.svg';
import SuccessImage from '@images/check-line.png';
import FailImage from '@images/close.png';
import FileImage from '@images/file.png';
import forceFailImage from '@images/force-fail.png';
import ForceRetryImage from '@images/force-retry.png';
import ForceSkipWarningImage from '@images/force-skip-warning.png';
import MinusImage from '@images/minus-fill.png';
import PlusImage from '@images/plus-fill.png';
import manualConfirmImage from '@images/querenjixu.png';
import RetryImage from '@images/refresh-2.png';
import SkipImage from '@images/skip.png';
import SkipSignImage from '@images/skip-2.png';
import PendingImage from '@images/sync-pending.png';
import WaitTodoImage from '@images/wait-todo.png';

import {
  Circle as GCircle,
  type DisplayObject,
  type Group,
  Image as GImage,
  Rect as GRect,
  Text as GText,
} from '@antv/g';
import { Rect, type UpsertHooks } from '@antv/g6';

import { type Node } from './layout';

const LINE_WIDTH = 168;

// 节点标题换行、耗时背景宽度都要测量文本，节点多时反复新建 canvas 开销明显，这里复用同一个上下文
const textMeasureContext = document.createElement('canvas').getContext('2d')!;

// 2行的情况下，对文本进行填充调整
function adjustLinesText(linesText: string[], keyword: string) {
  const adjustLines = linesText;
  const totalStr = linesText.join(keyword);
  const totalWidth = getTextWidth(totalStr);
  if (totalWidth < LINE_WIDTH) {
    return [totalStr];
  }
  const firstTestStr = `${linesText[0]}${keyword}`;
  let firstLineTestWidth = getTextWidth(firstTestStr);
  let secondLineStartIndex = 0;
  if (firstLineTestWidth < LINE_WIDTH) {
    while (firstLineTestWidth < LINE_WIDTH && firstLineTestWidth < totalWidth) {
      secondLineStartIndex += 1;
      const tmpStr = firstTestStr + linesText[1]!.substring(0, secondLineStartIndex);
      firstLineTestWidth = getTextWidth(tmpStr);
    }
    adjustLines[0] =
      secondLineStartIndex > 0 ? firstTestStr + linesText[1]!.substring(0, secondLineStartIndex) : firstTestStr;
  }
  if (adjustLines[0] === totalStr) {
    return [totalStr];
  }

  if (firstTestStr !== totalStr) {
    adjustLines[1] =
      secondLineStartIndex > 1 ? linesText[1]!.substring(secondLineStartIndex) : `${keyword}${linesText[1]}`;
  } else {
    if (!adjustLines[1] && totalStr.endsWith(keyword) && adjustLines[0] !== totalStr) {
      adjustLines[1] = keyword;
    }
  }
  return adjustLines.filter((item) => !!item);
}

function getTextWidth(text: string, fontStyle = '12px MicrosoftYaHei') {
  textMeasureContext.font = fontStyle; // 如 '16px MicrosoftYaHei'
  return textMeasureContext.measureText(text).width;
}

export class NormalNode extends Rect {
  /**
   * 本轮 renderNode 画过的图形 key。
   *
   * 用 declare 声明、在 renderNode 里建：基类构造函数里就会 render 一次，
   * 那时类字段的初始化还没执行，写成带初值的字段的话首轮直接读到 undefined，
   * 而且初始化轮到时又会把首轮记下的 key 冲掉
   */
  declare drawnKeys: Set<string>;
  /** renderNode 自己画过的全部图形 key，基类画的不在其中 */
  declare ownedKeys: Set<string>;

  private get statusMeta() {
    return NODE_STATUS_META[this.displayStatus];
  }

  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  get displayStatus() {
    return getNodeDisplayStatus(this.data);
  }

  get isFailed() {
    return this.displayStatus === 'FAILED';
  }

  get isRunning() {
    return this.displayStatus === 'RUNNING';
  }

  /** 时间标签按原始跳过标记判断：跳过的节点没有真实耗时可显示 */
  get isSkiped() {
    return this.data.skip || this.data.error_ignorable;
  }

  get isSubProcess() {
    return !!this.data.pipeline;
  }

  get isSuperUserMode() {
    return this.data.isSuperUserMode;
  }

  /**
   * 回收上一轮画过、这一轮没再画的图形。
   * 各 draw 方法都是「按状态命中一个分支就 return」，分支切换后旧分支的图形不会有人删，
   * 而节点元素跨轮询是复用的（见 flowGraph.initGraph 的 setData 路径），
   * 不清就会留下已完成节点上仍可点击的操作按钮、盖不住的旧状态图标、叠字的标题。
   * 只删差集，本轮还在画的图形仍是同一个实例，运行中节点的旋转动画不会断
   */
  clearStaleShapes(container: Group) {
    this.ownedKeys.forEach((key) => {
      if (this.drawnKeys.has(key)) {
        return;
      }
      // style 传 false 即删除图形，此时 Ctor 不参与逻辑
      this.upsert(key, GRect, false, container);
      this.ownedKeys.delete(key);
    });
  }

  drawBackgroundShape(attributes: any, container: Group) {
    const strokeColor = this.statusMeta.canvasStroke;

    const [width, height] = this.getSize(attributes);
    if (!width || !height) {
      return;
    }

    const backgroundShapeStyle = {
      fill: '#fff',
      height,
      radius: 8,
      shadowBlur: 4,
      shadowColor: attributes.nodeBackgroundshadowColor,
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      stroke: strokeColor,
      // 子流程节点的包围盒左侧留了 14px 空档给展开收起图标，卡片本身不占这一段
      width: this.isSubProcess ? width - 14 : width,
      x: this.isSubProcess ? -width / 2 + 14 : -width / 2,
      y: -height / 2,
    };
    this.upsertShape('backgroundShape', GRect, backgroundShapeStyle, container);
  }

  drawCollapseShape(attributes: any, container: Group) {
    if (!this.data.pipeline) {
      return;
    }

    const [width, height] = this.getSize(attributes);
    if (!width || !height) {
      return;
    }

    // 图标四角是透明的，卡片左边框的描边会从这里穿过去，先垫一层白底把图标处的边框遮断。
    // 必须在图标之前 upsert，同级图形按插入顺序叠放
    const collapseBackgroundStyle = {
      cx: -width / 2 + 14,
      cy: 0,
      fill: '#fff',
      r: 7,
    };
    this.upsertShape('collapseIconBackground', GCircle, collapseBackgroundStyle, container);

    const collapseIconStyle = {
      height: 14,
      src: this.data.isExpand ? MinusImage : PlusImage,
      width: 14,
      // 横跨在卡片左边框上：包围盒左侧的 14px 空档减去半个图标宽，纵向对齐节点中心
      x: -width / 2 + 7,
      y: -7,
    };

    this.upsertShape('collapseIcon', GImage, collapseIconStyle, container);
  }

  drawFocusBackgroundShape(attributes: any, container: Group) {
    const [width, height] = this.getSize(attributes);
    if (!width || !height) {
      return;
    }

    const focusBackgroundStyle = {
      fill: 'rgba(58, 132, 255, 0.1)',
      height: height + 16,
      radius: 2,
      stroke: '#3A84FF',
      visibility: attributes.focusNodeVisibility,
      width: width + (this.isSubProcess ? 9 : 16),
      x: -width / 2 - (this.isSubProcess ? 1 : 8),
      y: -height / 2 - 8,
    };
    this.upsertShape('focusBackground', GRect, focusBackgroundStyle, container);
  }

  drawNodeTitleShape(attributes: any, container: Group) {
    const [width] = this.getSize(attributes);
    if (!width) {
      return;
    }

    const { name, searchKey } = this.data;

    let y = 8;

    let lines = searchKey ? name!.split(new RegExp(encodeRegexp(searchKey))) : [name!];
    if (lines.length === 2) {
      lines = adjustLinesText(lines, searchKey);
    } else {
      if (getTextWidth(name!) > LINE_WIDTH) {
        y = 16;
      }
    }

    const nodeTitleStyleList = lines.map((text, index) => {
      return {
        fill: '#4D4F56',
        fontFamily: 'MicrosoftYaHei',
        fontSize: 12,
        maxLines: lines.length > 1 ? 1 : 2,
        text,
        textOverflow: 'ellipsis',
        wordWrap: true,
        wordWrapWidth: LINE_WIDTH,
        x: this.isSubProcess ? -width / 2 + 62 : -width / 2 + 48,
        y: lines.length > 1 ? index * 18 - 2 : y,
        zIndex: 1,
      };
    });

    nodeTitleStyleList.forEach((nodeTitleStyle, index) => {
      const lineText = nodeTitleStyle.text;
      if (searchKey && lineText.includes(searchKey)) {
        const textList = lineText.split(searchKey);
        textList.splice(1, 0, searchKey);
        textList.forEach((text, textIndex) => {
          if (!text) {
            return;
          }
          const style = _.cloneDeep(nodeTitleStyle);
          style.text = text;
          if (textIndex > 0) {
            const formalTextWidth = getTextWidth(textList.slice(0, textIndex).join(''));
            style.x = style.x + formalTextWidth;
            style.wordWrapWidth = LINE_WIDTH - formalTextWidth - getTextWidth(searchKey);
            style.maxLines = 1;
          }
          if (text === searchKey) {
            style.fill = 'orange';
          }
          this.upsertShape(`nodeTitle_${index}_${textIndex}`, GText, style, container);
        });
      } else {
        this.upsertShape(`nodeTitle_${index}`, GText, nodeTitleStyle, container);
      }
    });
  }

  drawOperationShape(attributes: any, container: Group) {
    if (this.isSubProcess || this.data.isTaskRevoked) {
      return;
    }
    const [width] = this.getSize(attributes);
    if (!width) {
      return;
    }

    const { retryable, skippable, status, todoId } = this.data;
    if (status === 'FAILED') {
      if (this.isSuperUserMode) {
        // 强制重试
        const forceRetryWraperStyle = {
          fill: '#F59500',
          height: 24,
          radius: 2,
          width: 80,
          x: -width / 2 + 4,
          y: 30,
        };
        this.upsertShape('forceRetryWraper', GRect, forceRetryWraperStyle, container);
        const {
          attributes: { x: rwX, y: rwY },
        } = this.getShape('forceRetryWraper');
        const retryIconStyle = {
          height: 12,
          src: ForceRetryImage,
          width: 12,
          x: rwX + 5,
          y: rwY + 6,
        };
        this.upsertShape('retryIcon', GImage, retryIconStyle, container);
        const {
          attributes: { x: riX, y: riY },
        } = this.getShape('retryIcon');
        const forceRetryTextStyle = {
          fill: '#FFFFFF',
          fontSize: 12,
          text: t('强制重试'),
          x: riX + 16,
          y: riY + 14,
        };
        this.upsertShape('forceRetryText', GText, forceRetryTextStyle, container);

        // 强制跳过
        const forceSkipWraperStyle = {
          fill: '#FDEED8',
          height: 24,
          radius: 2,
          width: 80,
          x: -width / 2 + 92,
          y: 30,
        };
        this.upsertShape('forceSkipWraper', GRect, forceSkipWraperStyle, container);
        const {
          attributes: { x: swX, y: swY },
        } = this.getShape('forceSkipWraper');
        const skipIconStyle = {
          height: 12,
          src: ForceSkipWarningImage,
          width: 12,
          x: swX + 4,
          y: swY + 5,
        };
        this.upsertShape('skipIcon', GImage, skipIconStyle, container);
        const {
          attributes: { x: siX, y: siY },
        } = this.getShape('skipIcon');
        const forceSkipTextStyle = {
          fill: '#E38B02',
          fontSize: 12,
          text: t('强制跳过'),
          x: siX + 16,
          y: siY + 15,
        };
        this.upsertShape('forceSkipText', GText, forceSkipTextStyle, container);
      } else {
        if (retryable) {
          // 失败重试
          const retryWraperStyle = {
            fill: attributes.retryOptFill,
            height: 24,
            radius: 2,
            width: 56,
            x: -width / 2 + 4,
            y: 30,
          };
          this.upsertShape('retryWraper', GRect, retryWraperStyle, container);
          const {
            attributes: { x: rwX, y: rwY },
          } = this.getShape('retryWraper');
          const retryIconStyle = {
            height: 12,
            src: RetryImage,
            width: 12,
            x: rwX + 5,
            y: rwY + 6,
          };
          this.upsertShape('retryIcon', GImage, retryIconStyle, container);
          const {
            attributes: { x: riX, y: riY },
          } = this.getShape('retryIcon');
          const retryTextStyle = {
            fill: '#4D4F56',
            fontSize: 12,
            text: t('重试'),
            x: riX + 17,
            y: riY + 14,
          };
          this.upsertShape('retryText', GText, retryTextStyle, container);
        }
        if (skippable) {
          // 跳过
          const skipWraperStyle = {
            fill: attributes.skipOptFill,
            height: 24,
            radius: 2,
            width: 56,
            x: retryable ? -width / 2 + 68 : -width / 2 + 4,
            y: 30,
          };
          this.upsertShape('skipWraper', GRect, skipWraperStyle, container);
          const {
            attributes: { x: swX, y: swY },
          } = this.getShape('skipWraper');
          const skipIconStyle = {
            height: 12,
            src: SkipImage,
            width: 12,
            x: swX + 4,
            y: swY + 5,
          };
          this.upsertShape('skipIcon', GImage, skipIconStyle, container);
          const {
            attributes: { x: siX, y: siY },
          } = this.getShape('skipIcon');
          const skipTextStyle = {
            fill: '#4D4F56',
            fontSize: 12,
            text: t('跳过'),
            x: siX + 18,
            y: siY + 15,
          };
          this.upsertShape('skipText', GText, skipTextStyle, container);
        }
      }
      // ai日志分析
      if (window.PROJECT_CONFIG.AI_LOG_ANALYSIS_OPEN) {
        const aiLogAnalysisWraperStyleX = () => {
          const count = [retryable, skippable].filter(Boolean).length;
          return -width / 2 + 64 * count + 4;
        };
        const aiLogAnalysisWraperStyle = {
          fill: attributes.aiLogOptFill,
          height: 24,
          radius: 2,
          width: 76,
          x: this.isSuperUserMode ? -width / 2 + 180 : aiLogAnalysisWraperStyleX(),
          y: 30,
        };
        this.upsertShape('aiLogAnalysisWraper', GRect, aiLogAnalysisWraperStyle, container);
        const {
          attributes: { x: aX, y: aY },
        } = this.getShape('aiLogAnalysisWraper');
        const aiLogAnalysisIconStyle = {
          height: 12,
          src: AiBluekingImage,
          width: 12,
          x: aX + 5,
          y: aY + 6,
        };
        this.upsertShape('aiLogAnalysisIcon', GImage, aiLogAnalysisIconStyle, container);
        const {
          attributes: { x: aiiX, y: aiiY },
        } = this.getShape('aiLogAnalysisIcon');
        const aiLogAnalysisTextStyle = {
          fill: '#4D4F56',
          fontSize: 12,
          text: t('日志解析'),
          x: aiiX + 15,
          y: aiiY + 14,
        };
        this.upsertShape('aiLogAnalysisText', GText, aiLogAnalysisTextStyle, container);
      }
      return;
    }
    if (todoId) {
      // 人工确认
      const manualConfirmWraperStyle = {
        fill: attributes.manualOptFill,
        height: 24,
        radius: 2,
        width: 80,
        x: -width / 2 + 4,
        y: 30,
      };
      this.upsertShape('manualConfirmWraper', GRect, manualConfirmWraperStyle, container);
      const {
        attributes: { x: mcwX, y: mcwY },
      } = this.getShape('manualConfirmWraper');
      const manualConfirmIconStyle = {
        height: 14,
        src: manualConfirmImage,
        width: 14,
        x: mcwX + 5,
        y: mcwY + 5,
      };
      this.upsertShape('manualConfirmIcon', GImage, manualConfirmIconStyle, container);
      const {
        attributes: { x: mciX, y: mciY },
      } = this.getShape('manualConfirmIcon');
      const manualConfirmTextStyle = {
        fill: '#4D4F56',
        fontSize: 12,
        text: t('确认继续'),
        x: mciX + 18,
        y: mciY + 15,
      };
      this.upsertShape('manualConfirmText', GText, manualConfirmTextStyle, container);
      // 强制失败
      const forceFailWraperStyle = {
        fill: attributes.forceFailOptFill,
        height: 24,
        radius: 2,
        width: 80,
        x: -width / 2 + 92,
        y: 30,
      };
      this.upsertShape('forceFailWraper', GRect, forceFailWraperStyle, container);
      const {
        attributes: { x: ffwX, y: ffwY },
      } = this.getShape('forceFailWraper');
      const forceFailIconStyle = {
        height: 14,
        src: forceFailImage,
        width: 14,
        x: ffwX + 5,
        y: ffwY + 5,
      };
      this.upsertShape('forceFailIcon', GImage, forceFailIconStyle, container);
      const {
        attributes: { x: ffiX, y: ffiY },
      } = this.getShape('forceFailIcon');
      const forceFailTextStyle = {
        fill: '#4D4F56',
        fontSize: 12,
        text: t('强制失败'),
        x: ffiX + 18,
        y: ffiY + 15,
      };
      this.upsertShape('forceFailText', GText, forceFailTextStyle, container);
      return;
    }
    if (status === 'RUNNING') {
      // 强制失败
      const forceFailWraperStyle = {
        fill: attributes.forceFailOptFill,
        height: 24,
        radius: 2,
        width: 80,
        x: -width / 2 + 4,
        y: 30,
      };
      this.upsertShape('forceFailWraper', GRect, forceFailWraperStyle, container);
      const {
        attributes: { x: ffwX, y: ffwY },
      } = this.getShape('forceFailWraper');
      const forceFailIconStyle = {
        height: 14,
        src: forceFailImage,
        width: 14,
        x: ffwX + 5,
        y: ffwY + 5,
      };
      this.upsertShape('forceFailIcon', GImage, forceFailIconStyle, container);
      const {
        attributes: { x: ffiX, y: ffiY },
      } = this.getShape('forceFailIcon');
      const forceFailTextStyle = {
        fill: '#4D4F56',
        fontSize: 12,
        text: t('强制失败'),
        x: ffiX + 18,
        y: ffiY + 15,
      };
      this.upsertShape('forceFailText', GText, forceFailTextStyle, container);
      return;
    }
  }

  drawRetryDisplayShape(_: any, container: Group) {
    if (!this.isFailed || this.isSubProcess || !this.data.retry) {
      return;
    }

    // 重试次数是贴着耗时背景右侧画的，耗时背景没画出来（如失败自动跳过的节点）就没有落脚点
    const timeDisplayBackground = this.getShape('timeDisplayBackground');
    if (!timeDisplayBackground) {
      return;
    }

    const {
      attributes: { width, x: timeX, y: timeY },
    } = timeDisplayBackground;
    const retryTextBackgroundStyle = {
      fill: '#979BA5',
      height: 14,
      radius: [2, 0, 0, 2],
      width: 26,
      x: timeX + width + 2,
      y: timeY,
    };
    this.upsertShape('retryDisplayTextBackground', GRect, retryTextBackgroundStyle, container);
    const retryTextStyle = {
      fill: '#fff',
      fontSize: 9,
      text: t('重试'),
      x: timeX + width + 6,
      y: timeY + 14,
    };
    this.upsertShape('retryDisplayText', GText, retryTextStyle, container);
    const retryCountBackgroundStyle = {
      fill: '#DCDEE5',
      height: 14,
      radius: [0, 2, 2, 0],
      width: 14,
      x: timeX + width + 28,
      y: timeY,
    };
    this.upsertShape('retryCountBackground', GRect, retryCountBackgroundStyle, container);
    const retryCountNumberStyle = {
      fill: '#4D4F56',
      fontSize: 9,
      text: `${this.data.retry}`,
      x: timeX + width + 32,
      y: timeY + 14,
    };
    this.upsertShape('retryCountNumber', GText, retryCountNumberStyle, container);
  }

  drawStatusShape(attributes: any, container: Group) {
    const [width, height] = this.getSize(attributes);
    if (!width || !height) {
      return;
    }

    // 矩形背景
    const mainStatusBackgroundStyle = {
      fill: this.statusMeta.canvasFill,
      height: 32,
      radius: 4,
      width: 32,
      x: -width / 2 + (this.isSubProcess ? 22 : 8),
      y: -height / 2 + 8,
    };
    this.upsertShape('mainStatusBackground', GRect, mainStatusBackgroundStyle, container);
    // 节点左侧图标
    const mainStatusImageStyle = {
      height: 17.5,
      src: FileImage,
      width: 15,
      x: -width / 2 + (this.isSubProcess ? 31 : 17),
      y: -height / 2 + 15,
    };
    this.upsertShape('mainStatusImage', GImage, mainStatusImageStyle, container);
    if (this.displayStatus !== 'CREATED') {
      // 右上角图标公共白色背景
      const rightTopBackgroundStyle = {
        cx: width / 2,
        cy: -height / 2,
        fill: '#FFF',
        r: 11,
      };
      this.upsertShape('rightTopBackground', GCircle, rightTopBackgroundStyle, container);
    }

    if (this.isFailed) {
      // 失败图标
      const failedBackgroundStyle = {
        cx: width / 2,
        cy: -height / 2,
        fill: attributes.failedImageBackgroundColor,
        r: 9,
      };
      this.upsertShape('rightTopFailedImageBackground', GCircle, failedBackgroundStyle, container);
      const failedImageStyle = {
        height: 16,
        src: FailImage,
        width: 16,
        x: width / 2 - 8,
        y: -height / 2 - 8,
      };
      this.upsertShape('rightTopFailedImage', GImage, failedImageStyle, container);
      return;
    }

    if (this.displayStatus === 'TODO') {
      // 待继续图标
      const todoBackgroundStyle = {
        cx: width / 2,
        cy: -height / 2,
        fill: attributes.todoImageBackgroundColor,
        r: 9,
      };
      this.upsertShape('rightTopTodoImageBackground', GCircle, todoBackgroundStyle, container);
      const todoImageStyle = {
        height: 14,
        src: WaitTodoImage,
        width: 14,
        x: width / 2 - 7,
        y: -height / 2 - 7,
      };
      this.upsertShape('rightTopTodoImage', GImage, todoImageStyle, container);
      return;
    }

    // 准备中与执行中共用这个分支
    if (this.isRunning || this.displayStatus === 'READY') {
      // 绘制执行中loading
      const loadingBackgroundStyle = {
        cx: width / 2,
        cy: -height / 2,
        fill: attributes.loadingImageBackgroundColor,
        r: 9,
      };
      this.upsertShape('rightTopLoadingImageBackground', GCircle, loadingBackgroundStyle, container);
      const loadingImageStyle = {
        height: 14,
        src: PendingImage,
        transformOrigin: 'center center',
        width: 14,
        x: width / 2 - 7,
        y: -height / 2 - 7,
      };
      // 挂在 afterCreate 上：只在图形新建时启动旋转，复用旧图形时动画还在，重挂会把角度归零。
      // 不能改用节点的 onCreate，它只在节点元素创建时触发一次，
      // 而失败重试回到执行中时这个图形是被 clearStaleShapes 收掉后重建的
      this.upsertShape('rightTopLoadingImage', GImage, loadingImageStyle, container, {
        afterCreate: (loadingImage) => {
          loadingImage.animate([{ transform: 'rotate(0deg)' }, { transform: 'rotate(-360deg)' }], {
            direction: 'normal',
            duration: 3000,
            easing: 'linear',
            iterations: Infinity,
          });
        },
      });
      return;
    }
    if (this.displayStatus === 'SKIPPED') {
      // 绘制已跳过
      const skipedTipWraperStyle = {
        fill: '#8EBF76',
        height: 14,
        radius: 2,
        width: 60,
        x: -width / 2 + (this.isSubProcess ? 18 : 4),
        y: -height / 2 - 16,
      };
      this.upsertShape('rightTopSkipedTipWraper', GRect, skipedTipWraperStyle, container);
      const {
        attributes: { x: stwX, y: stwY },
      } = this.getShape('rightTopSkipedTipWraper');
      const skipTextStyle = {
        fill: '#fff',
        fontSize: 9,
        text: this.data.error_ignorable ? t('失败自动跳过') : t('失败手动跳过'),
        x: stwX + 3,
        y: stwY + 13,
      };
      this.upsertShape('rightTopSkipText', GText, skipTextStyle, container);

      // 已跳过图标
      const skipeBackgroundStyle = {
        cx: width / 2,
        cy: -height / 2,
        fill: attributes.skipImageBackgroundColor,
        r: 9,
      };
      this.upsertShape('rightTopSkipImageBackground', GCircle, skipeBackgroundStyle, container);
      const skipeImageStyle = {
        height: 12,
        src: SkipSignImage,
        width: 12,
        x: width / 2 - 6,
        y: -height / 2 - 7,
      };
      this.upsertShape('rightTopSkipImage', GImage, skipeImageStyle, container);
      return;
    }

    if (this.displayStatus === 'FINISHED') {
      // 完成图标
      const finishedBackgroundStyle = {
        cx: width / 2,
        cy: -height / 2,
        fill: attributes.finishedImageBackgroundColor,
        r: 9,
      };
      this.upsertShape('rightTopFinishedImageBackground', GCircle, finishedBackgroundStyle, container);
      const finishedImageStyle = {
        height: 12,
        src: SuccessImage,
        width: 12,
        x: width / 2 - 6,
        y: -height / 2 - 6,
      };
      this.upsertShape('rightTopFinishedImage', GImage, finishedImageStyle, container);
    }
  }

  drawTimeDisplayShape(attributes: any, container: Group) {
    if (!this.data.started_at || this.isSkiped) {
      return;
    }

    const [width, height] = this.getSize(attributes);
    if (!width || !height) {
      return;
    }

    const diffSeconds = this.isRunning
      ? Math.floor(Date.now() / 1000) - this.data.started_at
      : this.data.updated_at - this.data.started_at;
    const timeDisplayText = getCostTimeDisplay(diffSeconds);
    const timeDisplayTextStyle = {
      fill: '#fff',
      fontSize: 9,
      text: timeDisplayText,
      x: -width / 2 + (this.isSubProcess ? 22 : 8),
      y: -height / 2 - 3,
      zIndex: 2,
    };
    this.upsertShape('timeDisplayText', GText, timeDisplayTextStyle, container);

    const {
      attributes: { x: textX, y: textY },
    } = this.getShape('timeDisplayText');
    const backgroundWidth = getTextWidth(timeDisplayText, '9px MicrosoftYaHei');
    const timeDisplayBackgroundStyle = {
      fill: '#979BA5',
      height: 14,
      radius: 2,
      width: backgroundWidth + 6,
      x: textX - 2,
      y: textY - 14,
      zindex: 1,
    };

    this.upsertShape('timeDisplayBackground', GRect, timeDisplayBackgroundStyle, container);
  }

  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }

  renderNode(attributes: any, container: Group) {
    this.drawnKeys = new Set();
    this.ownedKeys ??= new Set();
    this.drawFocusBackgroundShape(attributes, container);
    this.drawBackgroundShape(attributes, container);
    this.drawTimeDisplayShape(attributes, container);
    this.drawStatusShape(attributes, container);
    this.drawNodeTitleShape(attributes, container);
    this.drawCollapseShape(attributes, container);
    this.drawOperationShape(attributes, container);
    this.drawRetryDisplayShape(attributes, container);
    this.clearStaleShapes(container);
  }

  /** 与基类 upsert 的唯一区别是记下 key，好让 clearStaleShapes 知道哪些图形归自己管 */
  upsertShape<T extends DisplayObject>(
    key: string,
    Ctor: new (...args: any[]) => T,
    style: T['attributes'],
    container: Group,
    hooks?: UpsertHooks,
  ) {
    this.drawnKeys.add(key);
    this.ownedKeys.add(key);
    this.upsert(key, Ctor, style, container, hooks);
  }
}
