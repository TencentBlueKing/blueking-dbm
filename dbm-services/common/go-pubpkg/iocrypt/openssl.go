package iocrypt

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/pkg/errors"
	"golang.org/x/exp/slices"
)

// Openssl EncryptTool
type Openssl struct {
	CryptCmd    string
	EncryptElgo AlgoType
	// EncryptKey passphrase used to encrypt something
	EncryptKey string
	// EncryptKeyFile passphrase from file used to encrypt something
	EncryptKeyFile string
}

const (
	AlgoAES256CBC AlgoType = "aes-256-cbc"
	AlgoAES192CBC AlgoType = "aes-128-cbc"
	AlgoSM4CBC    AlgoType = "sm4-cbc" // need openssl>=1.1.1
)

var opensslAllowedAlgos = []AlgoType{AlgoAES256CBC, AlgoAES192CBC, AlgoSM4CBC}

// BuildCommand implement BuildCommand
func (e Openssl) BuildCommand(ctx context.Context) (*exec.Cmd, error) {
	if !slices.Contains(opensslAllowedAlgos, e.EncryptElgo) {
		return nil, errors.Errorf("unknown crypt algorithm: %s", e.EncryptElgo)
	}
	cmdArgs := []string{"enc", fmt.Sprintf("-%s", e.EncryptElgo), "-e", "-salt"} // >=1.1.1 "-pbkdf2"

	if e.EncryptKeyFile != "" {
		cmdArgs = append(cmdArgs, "-kfile", e.EncryptKeyFile)
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

// DefaultSuffix return default suffix for encrypt tool
func (e Openssl) DefaultSuffix() string {
	return "enc"
}

// Name return encrypt tool name
func (e Openssl) Name() string {
	return e.CryptCmd
}
