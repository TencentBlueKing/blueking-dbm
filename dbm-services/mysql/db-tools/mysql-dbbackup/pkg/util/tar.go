// Package util TODO
package util

import (
	"archive/tar"
	"fmt"
	"io"
	"os"
	"sync"

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
	if err := t.tarWriter.Close(); err != nil {
		_ = t.destFileWriter.Close()
		return err
	}
	if t.Encrypt {
		return t.destEncryptWriter.Close()
	} else {
		return t.destFileWriter.Close()
	}
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
