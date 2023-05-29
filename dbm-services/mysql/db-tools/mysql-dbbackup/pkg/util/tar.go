/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package util TODO
package util

import (
	"archive/tar"
	"fmt"
	"io"
	"os"
	"sync"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/iocrypt"
)

// TarWriterFiles tarFile: writer object
type TarWriterFiles struct {
	TarFiles  map[string]*TarWriter
	IOLimitMB int
}

// TarWriter TODO
type TarWriter struct {
	IOLimitMB   int
	EncryptTool iocrypt.EncryptTool
	Encrypt     bool

	tarSize           uint64
	destFileWriter    *os.File
	destEncryptWriter io.WriteCloser
	tarWriter         *tar.Writer
	mu                sync.Mutex

	splitWriter *SplitWriter
}

type TarSplitWriter struct {
	tarWriter TarWriter

	SuffixFormat string
	ChunkSize    uint64
}

// NewSplit splitSize bytes
func (t *TarWriter) NewSplit(dstTarName string, splitSize int) (err error) {
	if splitSize < 1024*1024 {
		return errors.Errorf("split file size is too small %d", splitSize)
	}
	splitWriter := &SplitWriter{
		FileName:        dstTarName,
		SplitSize:       splitSize,
		outFileNameTmpl: fmt.Sprintf(`%s.part_%s`, dstTarName, "%d"), // need to be same with const ReSplitPart
	}
	if err != nil {
		return err
	}
	if t.Encrypt {
		t.destEncryptWriter, err = iocrypt.FileEncryptWriter(t.EncryptTool, splitWriter)
		if err != nil {
			fmt.Println("TarWriter new error", err)
			return err
		}
		t.tarWriter = tar.NewWriter(t.destEncryptWriter)
	} else {
		t.tarWriter = tar.NewWriter(splitWriter)
	}

	t.splitWriter = splitWriter
	return nil
}

func (t *TarWriter) GetSplitTars() map[string]int {
	return t.splitWriter.ReturnFiles()
}

// New TODO
// init tarWriter destFileWriter destEncryptWriter
// will open destFile
// destFileWriter or destEncryptWriter need to close outside
// need to call tarWriter.Close()
func (t *TarWriter) New(dstTarName string) (err error) {
	t.destFileWriter, err = os.Create(dstTarName)
	if err != nil {
		return err
	}
	if t.Encrypt {
		t.destEncryptWriter, err = iocrypt.FileEncryptWriter(t.EncryptTool, t.destFileWriter)
		if err != nil {
			fmt.Println("TarWriter new error", err)
			return err
		}
		t.tarWriter = tar.NewWriter(t.destEncryptWriter)
	} else {
		t.tarWriter = tar.NewWriter(t.destFileWriter)
	}
	return nil
}

// WriteTar TODO
func (t *TarWriter) WriteTar(header *tar.Header, srcFile string) (isFile bool, written int64, err error) {
	t.mu.Lock()
	defer t.mu.Unlock()
	isFile = true
	if err = t.tarWriter.WriteHeader(header); err != nil {
		return isFile, 0, err
	}

	if !header.FileInfo().Mode().IsRegular() {
		isFile = false
		return isFile, 0, nil
	}
	rFile, err := os.Open(srcFile)
	if err != nil {
		return isFile, 0, err
	}
	defer rFile.Close()

	written, err = cmutil.IOLimitRate(t.tarWriter, rFile, int64(t.IOLimitMB))
	if err != nil {
		return isFile, 0, err
	}
	return isFile, written, nil
}

// Close tar writer
// will close destFile
// close won't reset IOLimitMB EncryptTool, could reuse it with new tarFilename
func (t *TarWriter) Close() error {
	defer func() {
		if t.Encrypt {
			t.destEncryptWriter.Close()
		} else {
			if t.splitWriter != nil {
				t.splitWriter.Close() // err?
			}
			if t.destFileWriter != nil {
				t.destFileWriter.Close()
			}
		}
	}()
	if err := t.tarWriter.Close(); err != nil {
		return err
	}
	return nil
}

/*func tarCmd(filepath string, cnf *parsecnf.CnfShared) error {
	tar_cmdstr := strings.Join([]string{"tar cf - ", filepath,
	" --remove-files | pv -L ", strconv.FormatUint(cnf.TarSpeed, 10), "m"}, "")
	output, err := exec.Command("/bin/bash", "-c", tar_cmdstr).CombinedOutput()
	if err != nil {
		logger.Log.Error("failed to tar")
	}
	if output != nil {
		logger.Log.Info("tar cmd, output: ", output)
	}
	return nil
}*/
