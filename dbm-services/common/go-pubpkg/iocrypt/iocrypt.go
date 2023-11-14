package iocrypt

import (
	"context"
	"io"
	"os/exec"

	"github.com/pkg/errors"
)

// EncryptTool usually Symmetric encryption
type EncryptTool interface {
	BuildCommand(ctx context.Context) (*exec.Cmd, error)
	DefaultSuffix() string
	Name() string
}

// AlgoType algorithm type
type AlgoType string

// FileEncryptWriter new
func FileEncryptWriter(cryptTool EncryptTool, w io.Writer) (io.WriteCloser, error) {
	if cryptTool == nil {
		return nil, errors.New("no crypt tool provide")
	}
	xbw := &FileEncrypter{CryptTool: cryptTool}
	if err := xbw.InitWriter(w); err != nil {
		return nil, err
	}
	return xbw, nil
}
