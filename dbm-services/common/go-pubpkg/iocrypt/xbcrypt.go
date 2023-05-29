package iocrypt

import (
	"context"
	"os/exec"

	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
)

// Xbcrypt EncryptTool
type Xbcrypt struct {
	CryptCmd       string
	EncryptElgo    AlgoType
	EncryptKey     string
	EncryptKeyFile string
}

const (
	AlgoAES256 AlgoType = "AES256"
	AlgoAES192 AlgoType = "AES192"
	AlgoAES128 AlgoType = "ASE128"
)

var xbcryptAllowedAlgos = []AlgoType{AlgoAES256, AlgoAES192, AlgoAES128}

// BuildCommand implement BuildCommand
func (e Xbcrypt) BuildCommand(ctx context.Context) (*exec.Cmd, error) {
	if !slices.Contains(xbcryptAllowedAlgos, e.EncryptElgo) {
		return nil, errors.Errorf("unknown crypt algorithm: %s", e.EncryptElgo)
	}
	cmdArgs := []string{"-a", string(e.EncryptElgo)} // –encrypt-threads
	if e.EncryptKeyFile != "" {
		cmdArgs = append(cmdArgs, "-f", e.EncryptKeyFile)
	} else if e.EncryptKey != "" {
		//keyHash := fmt.Sprintf("%x", md5.Sum([]byte(e.EncryptKey)))
		if len(e.EncryptKey)%16 != 0 {
			return nil, errors.Errorf("key len error(need N*16): %s", e.EncryptKey)
		}
		cmdArgs = append(cmdArgs, "-k", e.EncryptKey)
	} else {
		return nil, errors.New("no key provide")
	}
	return exec.CommandContext(ctx, e.CryptCmd, cmdArgs...), nil
}

// DefaultSuffix return suffix
func (e Xbcrypt) DefaultSuffix() string {
	return "xb"
}

// Name return name
func (e Xbcrypt) Name() string {
	return e.CryptCmd
}
