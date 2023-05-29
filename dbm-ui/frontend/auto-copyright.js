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

/* eslint-disable max-len */
const path = require('path');
const fs = require('fs');

const ignoreList = [
  path.join(__dirname, './public'),
  path.join(__dirname, './node_modules'),
  path.join(__dirname, './dist'),
];

const javascriptCopyright = [
  '/*',
  ' * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.',
  ' *',
  ' * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.',
  ' *',
  ' * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.',
  ' * You may obtain a copy of the License at https://opensource.org/licenses/MIT',
  ' *',
  ' * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed',
  ' * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for',
  ' * the specific language governing permissions and limitations under the License.',
  '*/',
];

const vueCopyright = [
  '<!--',
  ' * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.',
  ' *',
  ' * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.',
  ' *',
  ' * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.',
  ' * You may obtain a copy of the License athttps://opensource.org/licenses/MIT',
  ' *',
  ' * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed',
  ' * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for',
  ' * the specific language governing permissions and limitations under the License.',
  '-->',
];

const lincense = 'TencentBlueKing is pleased to support the open source community by making';

const readFileLines = (filePath, callback) => {
  const fileContent = fs.readFileSync(filePath, {
    encoding: 'utf8',
  });
  const lines = fileContent.split(/\n/);
  if (lines.length < 1) {
    return;
  }
  callback(lines, fileContent.indexOf(lincense) > 0);
};
const writeFileLines = (target, copyright, fileLines) => {
  fs.writeFileSync(target, `${copyright.join('\n')}\n\n${fileLines.join('\n')}`);
};

const copyright = (target) => {
  if (ignoreList.includes(target)) {
    return;
  }
  const state = fs.statSync(target);
  if (state.isFile()) {
    if (/.(js|ts|tsx|less)$/.test(target)) {
      console.log(`JAVASCRIPT: ${target}`);
      // javascript 文件
      readFileLines(target, (fileLines, oldLincense) => {
        let endIndex = 0; // copyright end
        if (/\/\*/.test(fileLines[0]) && oldLincense) {
          // eslint-disable-next-line no-plusplus
          for (let i = 0; i < fileLines.length; i++) {
            if (/\*\//.test(fileLines[i])) {
              endIndex = i + 2;
              break;
            }
          }
        }
        writeFileLines(target, javascriptCopyright, fileLines.slice(endIndex));
      });
    } else if (/.(vue|html)$/.test(target)) {
      console.log(`VUE: ${target}`);
      // vue 文件
      readFileLines(target, (fileLines, oldLincense) => {
        let endIndex = 0; // copyright end
        if (/<!--/.test(fileLines[0]) && oldLincense) {
          // eslint-disable-next-line no-plusplus
          for (let i = 0; i < fileLines.length; i++) {
            if (/-->/.test(fileLines[i])) {
              endIndex = i + 2;
              break;
            }
          }
        }
        writeFileLines(target, vueCopyright, fileLines.slice(endIndex));
      });
    }
  } else if (state.isDirectory()) {
    const dirList = fs.readdirSync(target);
    dirList.forEach((item) => {
      copyright(path.join(target, item));
    });
  }
};

copyright(path.join(__dirname, './'));
