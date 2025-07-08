import _ from 'lodash';

import { encodeRegexp, getCostTimeDisplay } from '@utils';

import manualConfirmImage from '@images/check.png';
import FileImage from '@images/file.png';
import forceFailImage from '@images/force-fail.png';
import MinusImage from '@images/minus-fill.png';
import AddImage from '@images/plus-fill.png';
import RetryImage from '@images/refresh-2.png';
import SkipImage from '@images/stop.png';
import PendingImage from '@images/sync-pending.png';
import WaitToRunImage from '@images/wait-to-run.png';
import WaitTodoImage from '@images/wait-todo.png';

import { Circle as GCircle, type Group, Image as GImage, Rect as GRect, Text as GText } from '@antv/g';
import { Rect } from '@antv/g6';

import { type Node } from './calculate';

// 搜索关键字
export const searchObj = {
  key: '',
};

const LINE_WIDTH = 170;

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

function getTextWidth(text: string, fontStyle = '12px Arial') {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d')!;
  ctx.font = fontStyle; // 如 '16px Arial'
  return ctx.measureText(text).width;
}

export class NormalNode extends Rect {
  get data() {
    return this.context.model.getNodeLikeDatum(this.id) as Node;
  }

  get isFailed() {
    return this.data.status === 'FAILED';
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

  drawBackgroundShape(_: any, container: Group) {
    const isSkiped = this.data.skip;
    let strokeColor = '#A1E3BA';
    if (this.isFailed) {
      strokeColor = '#F8B4B4';
    } else {
      if (isSkiped) {
        strokeColor = '#B3DF9E';
      }
      if (this.isRunning) {
        strokeColor = '#A3C5FD';
      }
      if (this.data.todoId) {
        strokeColor = '#F9D090';
      }
      if (this.isWaitToRun) {
        strokeColor = '#F0F1F5';
      }
    }
    const backgroundShapeStyle = {
      fill: '#fff',
      height: 60,
      radius: 4,
      shadowBlur: 4,
      shadowColor: '#1919290d',
      shadowOffsetX: 2,
      shadowOffsetY: 2,
      stroke: strokeColor,
      width: 240,
      x: this.isSubProcess ? -113 : -120,
      y: -30,
    };
    this.upsert('backgroundShape', GRect, backgroundShapeStyle, container);
  }

  drawCollapseShape(attributes: any, container: Group) {
    if (!this.data.pipeline) {
      return;
    }

    const [width, height] = this.getSize(attributes);
    const collapseIconStyle = {
      height: 14,
      src: this.data.collapsed ? MinusImage : AddImage,
      width: 14,
      x: -width / 2,
      y: -height / 2 + 24,
    };

    this.upsert('collapseIcon', GImage, collapseIconStyle, container);
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
        y = 16;
      }
    }

    const nodeTitleStyleList = lines.map((text, index) => {
      return {
        fill: '#000',
        fontFamily: 'Arial',
        fontSize: 12,
        maxLines: lines.length > 1 ? 1 : 2,
        text,
        textOverflow: 'ellipsis',
        wordWrap: true,
        wordWrapWidth: LINE_WIDTH,
        x: this.isSubProcess ? -width / 2 + 72 : -width / 2 + 58,
        y: lines.length > 1 ? index * 16 : y,
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
            style.wordWrapWidth = LINE_WIDTH - formalTextWidth;
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
    if (this.isSubProcess) {
      return;
    }
    const [width] = this.getSize(attributes);
    const { retryable, skippable, status, todoId } = this.data;
    if (status === 'FAILED') {
      if (skippable) {
        // 跳过
        const skipWraperStyle = {
          fill: '#EAEBF0',
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
          x: swX + 5,
          y: swY + 6,
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
          fill: '#EAEBF0',
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
          x: riX + 18,
          y: riY + 15,
        };
        this.upsert('retryText', GText, retryTextStyle, container);
      }
      return;
    }
    if (todoId) {
      // 人工确认
      const manualConfirmWraperStyle = {
        fill: '#EAEBF0',
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
        height: 12,
        src: manualConfirmImage,
        width: 12,
        x: mcwX + 5,
        y: mcwY + 6,
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
        fill: '#EAEBF0',
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
        x: ffiX + 19,
        y: ffiY + 16,
      };
      this.upsert('forceFailText', GText, forceFailTextStyle, container);
      return;
    }
    if (status === 'RUNNING') {
      // 强制失败
      const forceFailWraperStyle = {
        fill: '#EAEBF0',
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
        x: ffiX + 19,
        y: ffiY + 16,
      };
      this.upsert('forceFailText', GText, forceFailTextStyle, container);
      return;
    }
  }

  drawRetryDisplayShape(_: any, container: Group) {
    if (!this.isFailed || this.isSubProcess) {
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
    console.log('retryCount = ', this.data.retry);
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
    let strokeColor = '#2CAF5E';
    if (this.isFailed) {
      strokeColor = '#FF5656';
    } else {
      if (isSkiped) {
        strokeColor = '#7CB560';
      }

      if (this.isRunning) {
        strokeColor = '#3A84FF';
      }
      if (this.data.todoId) {
        strokeColor = '#F59500';
      }

      if (this.isWaitToRun) {
        strokeColor = '#F5F7FA';
      }
    }

    const [height, width] = this.getSize(attributes);
    const mainStatusBackgroundStyle = {
      fill: strokeColor,
      height: 40,
      radius: 4,
      width: 40,
      x: -height / 2 + (this.isSubProcess ? 24 : 10),
      y: -width / 2 + 10,
    };
    this.upsert('mainStatusBackground', GRect, mainStatusBackgroundStyle, container);
    const mainStatusImageStyle = {
      height: 17.5,
      src: this.isWaitToRun ? WaitToRunImage : FileImage,
      width: 15,
      x: -height / 2 + (this.isSubProcess ? 37 : 23),
      y: -width / 2 + 21,
    };
    this.upsert('mainStatusImage', GImage, mainStatusImageStyle, container);
    if (this.isFailed) {
      return;
    }

    if (this.data.todoId) {
      // 待继续图标
      const todoBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -30,
        fill: '#F59500',
        r: 12,
      };
      this.upsert('todoBackground', GCircle, todoBackgroundStyle, container);
      const todoImageStyle = {
        height: 14,
        src: WaitTodoImage,
        width: 14,
        x: this.isSubProcess ? 120 : 113,
        y: -37,
      };
      this.upsert('todoImage', GImage, todoImageStyle, container);
      return;
    }

    if (this.isRunning) {
      // 绘制执行中loading
      const loadingBackgroundStyle = {
        cx: this.isSubProcess ? 127 : 120,
        cy: -30,
        fill: '#3A84FF',
        r: 12,
      };
      this.upsert('loadingBackground', GCircle, loadingBackgroundStyle, container);
      const loadingImageStyle = {
        height: 14,
        src: PendingImage,
        width: 14,
        x: this.isSubProcess ? 120 : 113,
        y: -37,
      };
      this.upsert('loadingImage', GImage, loadingImageStyle, container);
      return;
    }
    if (this.data.skip) {
      // 绘制已跳过
      const skipedTipWraperStyle = {
        fill: '#8EBF76',
        height: 14,
        radius: 2,
        width: 35,
        x: -width * 2 + 4,
        y: -48,
      };
      this.upsert('skipedTipWraper', GRect, skipedTipWraperStyle, container);
      const {
        attributes: { x: stwX, y: stwY },
      } = this.getShape('skipedTipWraper');
      const skipTextStyle = {
        fill: '#fff',
        fontSize: 9,
        text: '已跳过',
        x: stwX + 4,
        y: stwY + 14,
      };
      this.upsert('skipText', GText, skipTextStyle, container);
    }
  }

  drawTimeDisplayShape(attributes: any, container: Group) {
    if (!this.data.started_at || this.data.skip) {
      return;
    }

    const [height, width] = this.getSize(attributes);
    const diffSeconds = this.isRunning
      ? Math.floor(Date.now() / 1000) - this.data.started_at
      : this.data.updated_at - this.data.started_at;
    const timeDisplayText = getCostTimeDisplay(diffSeconds);
    const timeDisplayTextStyle = {
      fill: '#fff',
      fontSize: 9,
      text: timeDisplayText,
      x: -width * 2 + 4,
      y: -height / 4 + 26,
      zIndex: 2,
    };
    this.upsert('timeDisplayText', GText, timeDisplayTextStyle, container);

    const {
      attributes: { x: textX, y: textY },
    } = this.getShape('timeDisplayText');
    const backgroundWidth = getTextWidth(timeDisplayText, '9px Arial');
    const timeDisplayBackgroundStyle = {
      fill: '#979BA5',
      height: 14,
      radius: 2,
      width: backgroundWidth + 8,
      x: textX - 2,
      y: textY - 14,
      zindex: 1,
    };

    this.upsert('timeDisplayBackground', GRect, timeDisplayBackgroundStyle, container);
  }

  renderNode(attributes: any, container: Group) {
    this.drawBackgroundShape(attributes, container);
    this.drawTimeDisplayShape(attributes, container);
    this.drawStatusShape(attributes, container);
    this.drawNodeTitleShape(attributes, container);
    this.drawCollapseShape(attributes, container);
    this.drawOperationShape(attributes, container);
    this.drawRetryDisplayShape(attributes, container);
  }

  // eslint-disable-next-line perfectionist/sort-classes
  render(attributes = this.parsedAttributes as any, container: Group) {
    super.render(attributes, container);
    this.renderNode(attributes, container);
  }
}
