package cmutil

import (
	"archive/tar"
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
)

func ExtractTarGz(gzipStream io.Reader, dstDir string) error {
	uncompressedStream, err := gzip.NewReader(gzipStream)
	if err != nil {
		return errors.New("ExtractTarGz: NewReader failed")
	}

	tarReader := tar.NewReader(uncompressedStream)

	for true {
		header, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return errors.WithMessage(err, "ExtractTarGz: Next() failed")
		}

		// 防止路径遍历攻击
		fileName := filepath.Join(dstDir, filepath.Clean(header.Name))
		if !strings.HasPrefix(fileName, filepath.Clean(dstDir)+string(os.PathSeparator)) {
			return fmt.Errorf("ExtractTarGz: illegal file path %q", header.Name)
		}

		switch header.Typeflag {
		case tar.TypeDir:
			if err := os.Mkdir(fileName, os.FileMode(header.Mode)); err != nil {
				return errors.WithMessage(err, "ExtractTarGz: Mkdir() failed: %s")
			} else {
				_ = os.Chtimes(fileName, header.AccessTime, header.ModTime)
			}
		case tar.TypeReg:
			//outFile, err := os.Create(fileName)
			outFile, err := os.OpenFile(fileName, os.O_CREATE|os.O_TRUNC|os.O_RDWR, os.FileMode(header.Mode))
			if err != nil {
				return errors.WithMessage(err, "ExtractTarGz: Create() failed")
			}

			if _, err = io.Copy(outFile, tarReader); err != nil {
				outFile.Close()
				return errors.WithMessage(err, "ExtractTarGz: Copy() failed: %s")
			} else {
				_ = os.Chtimes(fileName, header.AccessTime, header.ModTime)
			}
			outFile.Close()
		case tar.TypeSymlink:
			// 检查符号链接目标是否合法
			linkTarget := filepath.Clean(header.Linkname)
			if !strings.HasPrefix(linkTarget, filepath.Clean(dstDir)+string(os.PathSeparator)) {
				return fmt.Errorf("ExtractTarGz: unsafe symlink target %q", header.Linkname)
			}
			if err := os.MkdirAll(filepath.Dir(fileName), 0755); err != nil {
				return errors.WithMessage(err, "ExtractTarGz: MkdirAll() symlink parent failed")
			}
			if err := os.Symlink(linkTarget, fileName); err != nil {
				return errors.WithMessage(err, "ExtractTarGz: Symlink() failed")
			}
		default:
			return fmt.Errorf(
				"ExtractTarGz: uknown type: %v in %s",
				header.Typeflag,
				header.Name)
		}
	}
	return nil
}
