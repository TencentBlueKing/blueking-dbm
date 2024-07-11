/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

import (
	"fmt"
	"io"
	"os"
)

// SplitWriter split src io to splited files
type SplitWriter struct {
	// FileName used to build target filename, usually absolute path
	FileName  string
	SplitSize int
	// fileSplitMap filename:size
	fileSplitMap map[string]int
	// seq split file seq no
	seq int
	// currentFile current file name to write
	currentFile     string
	currentWriter   io.WriteCloser
	currentWritten  int
	totalWritten    int
	outFileNameTmpl string
}

// Write implementation
func (r *SplitWriter) Write(p []byte) (int, error) {
	var err error
	if r.currentWriter == nil {
		r.seq = 0
		r.currentFile = fmt.Sprintf(r.outFileNameTmpl, r.seq)
		if _, err := os.Stat(r.currentFile); !os.IsNotExist(err) {
			return 0, err
		}
		r.currentWriter, err = os.Create(r.currentFile)
		if err != nil {
			return 0, err
		}
		// 顺带初始化
		r.fileSplitMap = map[string]int{r.currentFile: r.currentWritten}
	}

	// Copy size bytes to output file
	written, err := r.currentWriter.Write(p)
	if err != nil {
		return 0, err
	}
	r.currentWritten += written
	r.totalWritten += written

	// 存在一种边界情况，当源输入刚好是 SplitSize *N 倍数，最后可能会创建一个空文件
	if r.currentWritten >= r.SplitSize {
		r.fileSplitMap[r.currentFile] = r.currentWritten // 设置正确的有效值
		r.currentWritten = 0
		if err = r.currentWriter.Close(); err != nil {
			return 0, err
		}

		// new writer
		r.seq++
		r.currentFile = fmt.Sprintf(r.outFileNameTmpl, r.seq)
		// Check for existing output file
		if _, err = os.Stat(r.currentFile); !os.IsNotExist(err) {
			return 0, err
		}
		// Create output file
		r.currentWriter, err = os.Create(r.currentFile)
		if err != nil {
			return 0, err
		}
		r.fileSplitMap[r.currentFile] = r.currentWritten // new file: r.currentWritten is 0
	}
	if written < len(p) && written < 32*1024 { // 32*1024 is file io stream size
		return written, err
	}
	return written, err
}

// Close implementation
func (r *SplitWriter) Close() error {
	// 最后一个 writer close
	if r.currentWriter != nil {
		r.fileSplitMap[r.currentFile] = r.currentWritten
		_ = r.currentWriter.Close()
		r.currentWriter = nil
	}
	return nil
}

// ReturnFiles return splitted filenames
func (r *SplitWriter) ReturnFiles() map[string]int {
	return r.fileSplitMap
}

// TotalWriten return total file written
func (r *SplitWriter) TotalWriten() int {
	return r.totalWritten
}
