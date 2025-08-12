import _ from 'lodash';

import { encodeRegexp, getCostTimeDisplay } from '@utils';

import SuccessImage from '@images/check-line.png';
import FailImage from '@images/close.png';
import FileImage from '@images/file.png';
import forceFailImage from '@images/force-fail.png';
// import MinusImage from '@images/minus.png';
import MinusImage from '@images/minus-fill.png';
import PlusImage from '@images/plus-fill.png';
// import PlusImage from '@images/plus.png';
import manualConfirmImage from '@images/querenjixu.png';
import RetryImage from '@images/refresh-2.png';
import SkipImage from '@images/skip.png';
import SkipSignImage from '@images/skip-2.png';
import PendingImage from '@images/sync-pending.png';
import WaitTodoImage from '@images/wait-todo.png';

import { Circle as GCircle, type Group, Image as GImage, Rect as GRect, Text as GText } from '@antv/g';
import { Rect } from '@antv/g6';

import { type Node } from './calculate';

// 搜索关键字
export const searchObj = {
  key: '',
};

const LINE_WIDTH = 185;

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
      const tmpStr = firstTestStr + linesText[1].substring(0, secondLineStartIndex);
      firstLineTestWidth = getTextWidth(tmpStr);
    }
    adjustLines[0] =
      secondLineStartIndex > 0 ? firstTestStr + linesText[1].substring(0, secondLineStartIndex) : firstTestStr;
  }
  if (adjustLines[0] === totalStr) {
    return [totalStr];
  }

  if (firstTestStr !== totalStr) {
    adjustLines[1] =
      secondLineStartIndex > 1 ? linesText[1].substring(secondLineStartIndex) : `${keyword}${linesText[1]}`;
  } else {
    if (!adjustLines[1] && totalStr.endsWith(keyword) && adjustLines[0] !== totalStr) {
      adjustLines[1] = keyword;
    }
  }
  return adjustLines.filter((item) => !!item);
}

function getTextWidth(text: string, fontStyle = '12px MicrosoftYaHei') {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;
  ctx.font = fontStyle; // 如 '16px MicrosoftYaHei'
  return ctx.measureText(text).width;
}

export class NormalNode extends Rect {
  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  get isFailed() {
    return ['FAILED', 'REVOKED'].includes(this.data.status);
  }

  get isFinished() {
    return this.data.status === 'FINISHED';
  }

  get isRunning() {
    return this.data.status === 'RUNNING';
  }

  get isSubProcess() {
    return !!this.data.pipeline;
  }

  get isWaitToRun() {
    return this.data.status === 'CREATED';
  }

  drawBackgroundShape(attributes: any, container: Group) {
    const isSkiped = this.data.skip;
    let strokeColor = '#A1E3BA';
    if (this.isFailed) {
      strokeColor = '#FF4D4D';
    } else {
      if (isSkiped) {
        strokeColor = '#7FBB44';
      }
      if (this.isRunning) {
        strokeColor = '#3A84FF';
      }
      if (this.data.todoId) {
        strokeColor = '#F59500';
      }
      if (this.isWaitToRun || !this.data.status) {
        strokeColor = '#F0F1F5';
      }
    }
    const backgroundShapeStyle = {
      fill: '#fff',
      height: 52,
      radius: 8,
      shadowBlur: 4,
      shadowColor: attributes.nodeBackgroundshadowColor,
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      stroke: strokeColor,
      width: 240,
      x: this.isSubProcess ? -113 : -120,
      y: -24,
    };
    this.upsert('backgroundShape', GRect, backgroundShapeStyle, container);
  }

  drawCollapseShape(attributes: any, container: Group) {
    if (!this.data.pipeline) {
      return;
    }

    const [width, height] = this.getSize(attributes);

    // const collapseBackgroundStyle = {
    //   cx: -120,
    //   cy: 0,
    //   fill: attributes.collapseBackgroundColor,
    //   r: 7,
    //   zIndex: 101,
    // };
    // this.upsert('collapseBackground', GCircle, collapseBackgroundStyle, container);

    const collapseIconStyle = {
      height: 14,
      src: this.data.isExpand ? MinusImage : PlusImage,
      width: 14,
      x: -width / 2,
      y: -height / 2 + 20,
      // zIndex: 102,
    };

    this.upsert('collapseIcon', GImage, collapseIconStyle, container);
  }

  drawFocusBackgroundShape(attributes: any, container: Group) {
    const [width, height] = this.getSize(attributes);
    const focusBackgroundStyle = {
      fill: 'rgba(58, 132, 255, 0.1)',
      height: height + 16,
      radius: 2,
      stroke: '#3A84FF',
      visibility: attributes.focusNodeVisibility,
      width: width + (this.isSubProcess ? 9 : 16),
      x: -width / 2 - (this.isSubProcess ? 1 : 8),
      y: -height / 2 - 6,
    };
    this.upsert('focusBackground', GRect, focusBackgroundStyle, container);
  }

  drawNodeTitleShape(attributes: any, container: Group) {
    const [width] = this.getSize(attributes);
    const { name } = this.data;

    let y = 10;

    let lines = searchObj.key ? name!.split(new RegExp(encodeRegexp(searchObj.key))) : [name!];
    if (lines.length === 2) {
      y = 10;
      lines = adjustLinesText(lines, searchObj.key);
    } else {
      if (getTextWidth(name!) > LINE_WIDTH) {
        y = 18;
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
        x: this.isSubProcess ? -width / 2 + 66 : -width / 2 + 52,
        y: lines.length > 1 ? index * 18 : y,
        zIndex: 1,
      };
    });

    nodeTitleStyleList.forEach((nodeTitleStyle, index) => {
      const lineText = nodeTitleStyle.text;
      if (searchObj.key && lineText.includes(searchObj.key)) {
        const textList = lineText.split(searchObj.key);
        textList.splice(1, 0, searchObj.key);
        textList.forEach((text, textIndex) => {
          if (!text) {
            return;
          }
          const style = _.cloneDeep(nodeTitleStyle);
          style.text = text;
          if (textIndex > 0) {
            const formalTextWidth = getTextWidth(textList.slice(0, textIndex).join(''));
            style.x = style.x + formalTextWidth;
            style.wordWrapWidth = LINE_WIDTH - formalTextWidth - getTextWidth(searchObj.key);
            style.maxLines = 1;
          }
          if (text === searchObj.key) {
            style.fill = 'orange';
          }
          this.upsert(`nodeTitle_${index}_${textIndex}`, GText, style, container);
        });
      } else {
        this.upsert(`nodeTitle_${index}`, GText, nodeTitleStyle, container);
      }
    });
  }

  drawOperationShape(attributes: any, container: Group) {
    if (this.isSubProcess || this.data.isTaskRevoked) {
      return;
    }
    const [width] = this.getSize(attributes);
    const { retryable, skippable, status, todoId } = this.data;
    if (status === 'FAILED') {
      if (skippable) {
        // 跳过
        const skipWraperStyle = {
          fill: attributes.skipOptFill,
          height: 24,
          radius: 2,
          width: 56,
          x: -width / 2 + 4,
          y: 34,
        };
        this.upsert('skipWraper', GRect, skipWraperStyle, container);
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
        this.upsert('skipIcon', GImage, skipIconStyle, container);
        const {
          attributes: { x: siX, y: siY },
        } = this.getShape('skipIcon');
        const skipTextStyle = {
          fill: '#4D4F56',
          fontSize: 12,
          text: '跳过',
          x: siX + 18,
          y: siY + 15,
        };
        this.upsert('skipText', GText, skipTextStyle, container);
      }
      if (retryable) {
        // 失败重试
        const retryWraperStyle = {
          fill: attributes.retryOptFill,
          height: 24,
          radius: 2,
          width: 56,
          x: skippable ? -width / 2 + 68 : -width / 2 + 4,
          y: 34,
        };
        this.upsert('retryWraper', GRect, retryWraperStyle, container);
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
        this.upsert('retryIcon', GImage, retryIconStyle, container);
        const {
          attributes: { x: riX, y: riY },
        } = this.getShape('retryIcon');
        const retryTextStyle = {
          fill: '#4D4F56',
          fontSize: 12,
          text: '重试',
          x: riX + 17,
          y: riY + 14,
        };
        this.upsert('retryText', GText, retryTextStyle, container);
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
        y: 34,
      };
      this.upsert('manualConfirmWraper', GRect, manualConfirmWraperStyle, container);
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
      this.upsert('manualConfirmIcon', GImage, manualConfirmIconStyle, container);
      const {
        attributes: { x: mciX, y: mciY },
      } = this.getShape('manualConfirmIcon');
      const manualConfirmTextStyle = {
        fill: '#4D4F56',
        fontSize: 12,
        text: '确认继续',
        x: mciX + 18,
        y: mciY + 15,
      };
      this.upsert('manualConfirmText', GText, manualConfirmTextStyle, container);
      // 强制失败
      const forceFailWraperStyle = {
        fill: attributes.forceFailOptFill,
        height: 24,
        radius: 2,
        width: 80,
        x: -width / 2 + 92,
        y: 34,
      };
      this.upsert('forceFailWraper', GRect, forceFailWraperStyle, container);
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
      this.upsert('forceFailIcon', GImage, forceFailIconStyle, container);
      const {
        attributes: { x: ffiX, y: ffiY },
      } = this.getShape('forceFailIcon');
      const forceFailTextStyle = {
        fill: '#4D4F56',
        fontSize: 12,
        text: '强制失败',
        x: ffiX + 18,
        y: ffiY + 15,
      };
      this.upsert('forceFailText', GText, forceFailTextStyle, container);
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
        y: 34,
      };
      this.upsert('forceFailWraper', GRect, forceFailWraperStyle, container);
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
      this.upsert('forceFailIcon', GImage, forceFailIconStyle, container);
      const {
        attributes: { x: ffiX, y: ffiY },
      } = this.getShape('forceFailIcon');
      const forceFailTextStyle = {
        fill: '#4D4F56',
        fontSize: 12,
        text: '强制失败',
        x: ffiX + 18,
        y: ffiY + 15,
      };
      this.upsert('forceFailText', GText, forceFailTextStyle, container);
      return;
    }
  }

  drawRetryDisplayShape(_: any, container: Group) {
    if (!this.isFailed || this.isSubProcess || !this.data.retry) {
      return;
    }

    const {
      attributes: { width, x: timeX, y: timeY },
    } = this.getShape('timeDisplayBackground');
    const retryTextBackgroundStyle = {
      fill: '#979BA5',
      height: 14,
      radius: [2, 0, 0, 2],
      width: 26,
      x: timeX + width + 2,
      y: timeY,
    };
    this.upsert('retryDisplayTextBackground', GRect, retryTextBackgroundStyle, container);
    const retryTextStyle = {
      fill: '#fff',
      fontSize: 9,
      text: '重试',
      x: timeX + width + 6,
      y: timeY + 14,
    };
    this.upsert('retryDisplayText', GText, retryTextStyle, container);
    const retryCountBackgroundStyle = {
      fill: '#DCDEE5',
      height: 14,
      radius: [0, 2, 2, 0],
      width: 14,
      x: timeX + width + 28,
      y: timeY,
    };
    this.upsert('retryCountBackground', GRect, retryCountBackgroundStyle, container);
    const retryCountNumberStyle = {
      fill: '#4D4F56',
      fontSize: 9,
      text: `${this.data.retry}`,
      x: timeX + width + 32,
      y: timeY + 14,
    };
    this.upsert('retryCountNumber', GText, retryCountNumberStyle, container);
  }

  drawStatusShape(attributes: any, container: Group) {
    const isSkiped = this.data.skip;
    let strokeColor = '#3DC2A6';
    if (this.isFailed) {
      strokeColor = '#FF4D4D';
    } else {
      if (isSkiped) {
        strokeColor = '#7FBB44';
      }
      if (this.isRunning) {
        strokeColor = '#3A84FF';
      }
      if (this.data.todoId) {
        strokeColor = '#F59500';
      }
      if (this.isWaitToRun || !this.data.status) {
        strokeColor = '#C4C6CC';
      }
    }

    const [width, height] = this.getSize(attributes);
    // 矩形背景
    const mainStatusBackgroundStyle = {
      fill: strokeColor,
      height: 40,
      radius: 4,
      width: 40,
      x: -width / 2 + (this.isSubProcess ? 20 : 6),
      y: -height / 2 + 8,
    };
    this.upsert('mainStatusBackground', GRect, mainStatusBackgroundStyle, container);
    // 节点左侧图标
    const mainStatusImageStyle = {
      height: 17.5,
      src: FileImage,
      width: 15,
      x: -width / 2 + (this.isSubProcess ? 33 : 19),
      y: -height / 2 + 19,
    };
    this.upsert('mainStatusImage', GImage, mainStatusImageStyle, container);
    if (this.data.status && !this.isWaitToRun) {
      // 右上角图标公共白色背景
      const rightTopBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -24,
        fill: '#FFF',
        r: 11,
      };
      this.upsert('rightTopBackground', GCircle, rightTopBackgroundStyle, container);
    }

    if (this.isFailed) {
      // 失败图标
      const failedBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -24,
        fill: attributes.failedImageBackgroundColor,
        r: 9,
      };
      this.upsert('rightTopFailedImageBackground', GCircle, failedBackgroundStyle, container);
      const failedImageStyle = {
        height: 16,
        src: FailImage,
        width: 16,
        x: this.isSubProcess ? 119 : 112,
        y: -32,
      };
      this.upsert('rightTopFailedImage', GImage, failedImageStyle, container);
      return;
    }

    if (this.data.todoId) {
      // 待继续图标
      const todoBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -24,
        fill: attributes.todoImageBackgroundColor,
        r: 9,
      };
      this.upsert('rightTopTodoImageBackground', GCircle, todoBackgroundStyle, container);
      const todoImageStyle = {
        height: 14,
        src: WaitTodoImage,
        width: 14,
        x: this.isSubProcess ? 120 : 113,
        y: -31,
      };
      this.upsert('rightTopTodoImage', GImage, todoImageStyle, container);
      return;
    }

    if (this.isRunning) {
      // 绘制执行中loading
      const loadingBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -24,
        fill: attributes.loadingImageBackgroundColor,
        r: 9,
      };
      this.upsert('rightTopLoadingImageBackground', GCircle, loadingBackgroundStyle, container);
      const loadingImageStyle = {
        height: 14,
        src: PendingImage,
        width: 14,
        x: this.isSubProcess ? 120 : 113,
        y: -31,
      };
      this.upsert('rightTopLoadingImage', GImage, loadingImageStyle, container);
      return;
    }
    if (this.data.skip) {
      // 绘制已跳过
      const skipedTipWraperStyle = {
        fill: '#8EBF76',
        height: 14,
        radius: 2,
        width: 34,
        x: -height * 2 - 12,
        y: -40,
      };
      this.upsert('rightTopSkipedTipWraper', GRect, skipedTipWraperStyle, container);
      const {
        attributes: { x: stwX, y: stwY },
      } = this.getShape('rightTopSkipedTipWraper');
      const skipTextStyle = {
        fill: '#fff',
        fontSize: 9,
        text: '已跳过',
        x: stwX + 3,
        y: stwY + 14,
      };
      this.upsert('rightTopSkipText', GText, skipTextStyle, container);

      // 已跳过图标
      const skipeBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -24,
        fill: attributes.skipImageBackgroundColor,
        r: 9,
      };
      this.upsert('rightTopSkipImageBackground', GCircle, skipeBackgroundStyle, container);
      const skipeImageStyle = {
        height: 12,
        src: SkipSignImage,
        width: 12,
        x: this.isSubProcess ? 121 : 114,
        y: -31,
      };
      this.upsert('rightTopSkipImage', GImage, skipeImageStyle, container);
      return;
    }

    if (this.isFinished) {
      // 完成图标
      const finishedBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -24,
        fill: attributes.finishedImageBackgroundColor,
        r: 9,
      };
      this.upsert('rightTopFinishedImageBackground', GCircle, finishedBackgroundStyle, container);
      const finishedImageStyle = {
        height: 12,
        src: SuccessImage,
        width: 12,
        x: this.isSubProcess ? 121 : 114,
        y: -30,
      };
      this.upsert('rightTopFinishedImage', GImage, finishedImageStyle, container);
    }
  }

  drawTimeDisplayShape(attributes: any, container: Group) {
    if (!this.data.started_at || this.data.skip) {
      return;
    }

    const [width, height] = this.getSize(attributes);
    const diffSeconds = this.isRunning
      ? Math.floor(Date.now() / 1000) - this.data.started_at
      : this.data.updated_at - this.data.started_at;
    const timeDisplayText = getCostTimeDisplay(diffSeconds);
    const timeDisplayTextStyle = {
      fill: '#fff',
      fontSize: 9,
      text: timeDisplayText,
      x: -height * 2 - 8,
      y: -width / 4 + 33,
      zIndex: 2,
    };
    this.upsert('timeDisplayText', GText, timeDisplayTextStyle, container);

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

    this.upsert('timeDisplayBackground', GRect, timeDisplayBackgroundStyle, container);
  }

  onCreate() {
    const loadingImage = this.shapeMap.loadingImage;
    if (loadingImage) {
      loadingImage.animate(
        [
          { transform: 'rotate(360deg)', transformOrigin: 'center center' },
          { transform: 'rotate(0deg)', transformOrigin: 'center center' },
        ],
        {
          direction: 'normal',
          duration: 3000,
          easing: 'linear',
          iterations: Infinity,
        },
      );
    }
  }

  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }

  renderNode(attributes: any, container: Group) {
    this.drawFocusBackgroundShape(attributes, container);
    this.drawBackgroundShape(attributes, container);
    this.drawTimeDisplayShape(attributes, container);
    this.drawStatusShape(attributes, container);
    this.drawNodeTitleShape(attributes, container);
    this.drawCollapseShape(attributes, container);
    this.drawOperationShape(attributes, container);
    this.drawRetryDisplayShape(attributes, container);
  }
}
