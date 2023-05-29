// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package tables

/*
  File system encoding components:

Code range Pattern            Number   Used Unused  Blocks
-----------------------------------------------------------------------------
00C0..017F [.][0..4][g..z] 5*20= 100   97     3  Latin1 Supplement + Ext A
0370..03FF [.][5..9][g..z] 5*20= 100   88    12  Greek + Coptic
0400..052F [.][g..z][0..6] 20*7= 140  140   137  Cyrillic
0530..058F [.][g..z][7..8] 20*2=  40   38     2  Armenian
2160..217F [.][g..z][9]    20*1=  20   16     4  Number Forms
0180..02AF [.][g..z][a..k] 28*11=220  203    17  Latin Ext B + IPA
1E00..0EFF [.][g..z][l..r] 20*7= 140  136     4  Latin Additional Extended
1F00..1FFF [.][g..z][s..z] 20*8= 160  144    16  Greek Extended
....  .... [.][a..f][g..z] 6*20= 120    0   120  RESERVED
24B6..24E9 [.][@][a..z]           26   26     0  Enclosed Alphanumerics
FF21..FF5A [.][a..z][@]           26   26     0  Full Width forms

All other characters are encoded using five bytes:

[.][0..9a..z][0..9a..z][0..9a..z][0..9a..z]

*/
