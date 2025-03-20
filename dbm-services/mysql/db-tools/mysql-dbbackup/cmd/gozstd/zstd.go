// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/klauspost/compress/zstd"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/cmd"
)

// DefaultZstdSuffix 默认 zstd 压缩文件后缀
const DefaultZstdSuffix = ".zst"

var (
	ZstdSuffix     = DefaultZstdSuffix
	Verbose        = 0
	Quiet          = true
	Threads        = 2
	RemoveOriginal = false
)

var zstdCmd = &cobra.Command{
	Use:          "gozstd",
	Short:        "zstd go binary",
	Long:         "zstd go binary",
	Version:      cmd.DbbackupVersion,
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) (err error) {
		decompress, _ := cmd.Flags().GetBool("decompress")
		fileOutput, _ := cmd.Flags().GetString("output")
		consoleOutput, _ := cmd.Flags().GetBool("console")
		// 全局变量
		if format, err := cmd.Flags().GetString("format"); err != nil {
			return err
		} else {
			ZstdSuffix = format
		}
		Threads, _ = cmd.Flags().GetInt("threads")
		RemoveOriginal, _ = cmd.Flags().GetBool("rm")
		Quiet, _ = cmd.Flags().GetBool("quiet")
		Verbose, _ = cmd.Flags().GetInt("verbose")

		input := cmd.Flags().Args()
		if len(input) > 1 && (fileOutput != "" || consoleOutput) {
			return errors.New("more than one input files should not has -o or -c")
		}
		if len(input) == 0 {
			// read from stdin
			if fileOutput == "" && !consoleOutput {
				return errors.New("read from stdin need -c or -o")
			}
			if decompress {
				err = DeCompressOneFile(cmd, "")
			} else {
				err = CompressOneFile(cmd, "")
			}
			if err != nil {
				return err
			}
		} else {
			// read files
			for _, inputFileName := range input {
				if strings.TrimSpace(inputFileName) == "" { // invalid empty filename
					continue
				}
				if decompress {
					err = DeCompressOneFile(cmd, inputFileName)
				} else {
					err = CompressOneFile(cmd, inputFileName)
				}
				if err != nil {
					return err
				}
			}
			return nil
		}
		return nil
	},
}

func init() {
	zstdCmd.Flags().StringP("output", "o", "", "result stored into file (only 1 output file)")
	zstdCmd.Flags().BoolP("force-write", "f", false, "Allows overwriting existing files")
	zstdCmd.Flags().BoolP("decompress", "d", false, "decompress file")
	zstdCmd.Flags().BoolP("console", "c", false, "write to standard output")
	zstdCmd.Flags().IntP("level", "L", 3, "compression level (1,3,7,11)")
	zstdCmd.Flags().BoolP("quiet", "q", true, "suppress warnings; specify twice to suppress errors too")
	zstdCmd.Flags().IntP("verbose", "v", 0, "verbose level")

	//zstdCmd.Flags().BoolP("preserve", "k", true, "preserve source file(s)")
	zstdCmd.Flags().Bool("rm", false, "remove source file(s) after successful de/compression")

	zstdCmd.Flags().IntP("threads", "T", 2, "de/compression threads")
	zstdCmd.Flags().String("format", DefaultZstdSuffix, "compress files to the .zst format")

	zstdCmd.MarkFlagsMutuallyExclusive("force-write", "console")
}

// CompressOneFile 压缩一个文件
// inputFileName = "" means read from stdin
func CompressOneFile(cmd *cobra.Command, inputFileName string) (err error) {
	var reader io.Reader
	var writer io.Writer
	consoleOutput, _ := cmd.Flags().GetBool("console")
	var outputFileName string
	if inputFileName == "" {
		reader = bufio.NewReader(os.Stdin)
		outputFileName, _ = cmd.Flags().GetString("output")
	} else {
		if strings.HasSuffix(inputFileName, ZstdSuffix) {
			//return errors.Errorf("decompress input file should has suffux .zst for %s", inputFileName)
		}
		inputFile, err := os.OpenFile(inputFileName, os.O_RDONLY, 0644)
		if err != nil {
			return errors.WithMessagef(err, "read input file %s", inputFileName)
		}
		defer inputFile.Close()
		reader = inputFile // reader
		outputFileName = inputFileName + ZstdSuffix
	}
	if consoleOutput {
		writer = os.Stdout // writer
	} else {
		var outputFile *os.File
		if forceWrite, _ := cmd.Flags().GetBool("force-write"); cmutil.FileExists(outputFileName) && !forceWrite {
			return errors.Errorf("output file %s already exists, -f to overwrite it", outputFileName)
		}
		outputFile, err = os.OpenFile(outputFileName, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
		if err != nil {
			return err
		}
		defer outputFile.Close()
		writer = outputFile // writer
	}

	compressLevel, _ := cmd.Flags().GetInt("level")
	if n, err := Compress(reader, writer, compressLevel, Threads); err != nil {
		return errors.WithMessagef(err, "compress %s", inputFileName)
	} else {
		if Verbose > 0 {
			fmt.Printf("compress %s after %d bytes\n", inputFileName, n)
		}
	}
	if RemoveOriginal && inputFileName != "" {
		return os.Remove(inputFileName)
	}
	return nil
}

// DeCompressOneFile 解压一个文件
// inputFileName = "" means read from stdin
func DeCompressOneFile(cmd *cobra.Command, inputFileName string) (err error) {
	var reader io.Reader
	var writer io.Writer
	consoleOutput, _ := cmd.Flags().GetBool("console")
	var outputFileName string
	if inputFileName == "" {
		reader = bufio.NewReader(os.Stdin)
		outputFileName, _ = cmd.Flags().GetString("output")
	} else {
		if !strings.HasSuffix(inputFileName, ZstdSuffix) {
			return errors.Errorf("decompress input file should has suffux .zst for %s", inputFileName)
		}
		inputFile, err := os.OpenFile(inputFileName, os.O_RDONLY, 0644)
		if err != nil {
			return errors.WithMessagef(err, "read input file %s", inputFileName)
		}
		defer inputFile.Close()
		reader = inputFile // reader
		outputFileName = strings.TrimSuffix(inputFileName, ZstdSuffix)
	}
	if consoleOutput {
		writer = os.Stdout // writer
	} else {
		var outputFile *os.File
		if forceWrite, _ := cmd.Flags().GetBool("force-write"); cmutil.FileExists(outputFileName) && !forceWrite {
			return errors.Errorf("output file %s already exists, -f to overwrite it", outputFileName)
		}
		outputFile, err = os.OpenFile(outputFileName, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
		if err != nil {
			return err
		}
		defer outputFile.Close()
		writer = outputFile // writer
	}
	if n, err := Decompress(reader, writer, Threads); err != nil {
		return errors.WithMessagef(err, "decompress %s", inputFileName)
	} else {
		if Verbose > 0 {
			fmt.Printf("decompress %s after %d bytes\n", inputFileName, n)
		}
	}
	if RemoveOriginal && inputFileName != "" {
		return os.Remove(inputFileName)
	}
	return nil
}

// Compress encoder
func Compress(in io.Reader, out io.Writer, level int, threads int) (int64, error) {
	enc, err := zstd.NewWriter(out,
		zstd.WithEncoderConcurrency(threads), zstd.WithEncoderLevel(zstd.EncoderLevelFromZstd(level)))
	if err != nil {
		return 0, err
	}
	bufTmp := make([]byte, 128*1024)
	n, err := io.CopyBuffer(enc, in, bufTmp)
	//n, err := io.Copy()
	if err != nil {
		enc.Close()
		return 0, err
	}
	return n, enc.Close()
}

// Decompress decoder
func Decompress(in io.Reader, out io.Writer, threads int) (int64, error) {
	dec, err := zstd.NewReader(in, zstd.WithDecoderConcurrency(threads))
	if err != nil {
		return 0, err
	}
	defer dec.Close()
	bufTmp := make([]byte, 128*1024)
	n, err := io.CopyBuffer(out, dec, bufTmp)
	//n, err := io.Copy(out, dec)
	return n, err
}

func main() {
	err := zstdCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}
