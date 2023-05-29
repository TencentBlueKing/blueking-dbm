// Package compress TODO
package compress

import (
	"bytes"
	"compress/gzip"
	"io/ioutil"
)

// GzipBytes TODO
func GzipBytes(in []byte) ([]byte, error) {
	var (
		buffer bytes.Buffer
		err    error
	)
	// writer := gzip.NewWriter(&buffer)
	writer, _ := gzip.NewWriterLevel(&buffer, 5)
	if _, err = writer.Write(in); err != nil {
		err = writer.Close()
		return nil, err
	}
	if err = writer.Close(); err != nil {
		return nil, err
	}
	return buffer.Bytes(), nil
}

// GunzipBytes TODO
func GunzipBytes(in []byte) ([]byte, error) {
	var out []byte
	reader, err := gzip.NewReader(bytes.NewReader(in))
	if err != nil {
		return nil, err
	}
	defer reader.Close()
	if out, err = ioutil.ReadAll(reader); err != nil {
		return nil, err
	}
	return out, nil
}
