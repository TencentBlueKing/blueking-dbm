// Package util TODO
package util

import (
	"archive/tar"
	"os"
	"sync"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/cmutil"
)

// TarWriterFiles tarFile: writer object
type TarWriterFiles struct {
	TarFiles  map[string]*TarWriter
	IOLimitMB int
}

// TarWriter TODO
type TarWriter struct {
	IOLimitMB int

	tarSize        uint64
	destFileWriter *os.File
	tarWriter      *tar.Writer
	mu             sync.Mutex
}

// New TODO
func (t *TarWriter) New(dstTarName string) (err error) {
	t.destFileWriter, err = os.Create(dstTarName)
	if err != nil {
		return err
	}
	t.tarWriter = tar.NewWriter(t.destFileWriter)
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

// Close TODO
func (t *TarWriter) Close() error {
	if err := t.tarWriter.Close(); err != nil {
		return err
	}
	if err := t.destFileWriter.Close(); err != nil {
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
