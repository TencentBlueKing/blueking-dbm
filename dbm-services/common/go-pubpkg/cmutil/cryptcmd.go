package cmutil

import (
	"fmt"
	"os/exec"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/iocrypt"
)

type EncryptOpt struct {
	// EncryptEnable 是否启用备份文件加密（对称加密），加密密码 passphrase 随机生成
	// EncryptEnable 为 true 时，EncryptTool EncryptPublicKey 有效
	EncryptEnable bool `ini:"EncryptEnable" json:"encrypt_enable" `
	// 加密工具，支持 openssl,xbcrypt，如果是xbcrypt 请指定路径
	EncryptCmd string `ini:"EncryptCmd" json:"encrypt_cmd"`
	// EncryptAlgo encrypt algorithm, leave it empty has default algorithm
	//  openssl [aes-256-cbc, aes-128-cbc, sm4-cbc]
	//  xbcrypt [AES256, AES192, AES128]
	EncryptAlgo iocrypt.AlgoType `ini:"EncryptElgo" json:"encrypt_algo"`
	// EncryptPublicKey public key 文件，对 passphrase 加密，上报加密字符串
	// 需要对应的平台 私钥 secret key 才能对 加密后的passphrase 解密
	// EncryptPublicKey 如果为空，会上报密码，仅测试用途
	EncryptPublicKey string `ini:"EncryptPublicKey" json:"encrypt_public_key"`

	encryptTool         iocrypt.EncryptTool
	passPhrase          string
	encryptedPassPhrase string
}

// SetEncryptTool tool can not change outside
func (e *EncryptOpt) SetEncryptTool(t iocrypt.EncryptTool) {
	e.encryptTool = t
}

// GetEncryptTool return encryptTool
// should Init first
func (e *EncryptOpt) GetEncryptTool() iocrypt.EncryptTool {
	return e.encryptTool
}

// GetEncryptedKey return encryptedPassPhrase to report
// should Init first
func (e *EncryptOpt) GetEncryptedKey() string {
	return e.encryptedPassPhrase
}

// GetPassphrase return passPhrase
// should Init first
func (e *EncryptOpt) GetPassphrase() string {
	return e.passPhrase
}

// Init 判断加密工具合法性
// 生成公钥加密后的密码
func (e *EncryptOpt) Init() (err error) {
	if e.EncryptCmd == "" {
		e.EncryptCmd = "openssl"
	}
	if _, err = exec.LookPath(e.EncryptCmd); err != nil {
		return err
	}
	e.passPhrase = RandomString(32) // symmetric encrypt key to encrypt files
	if e.EncryptPublicKey == "" {
		e.encryptedPassPhrase = e.passPhrase // not encrypted actually, just for report
	} else {
		if e.encryptedPassPhrase, err = iocrypt.EncryptStringWithPubicKey(e.passPhrase, e.EncryptPublicKey); err != nil {
			return err
		}
	}
	if strings.Contains(e.EncryptCmd, "openssl") {
		if e.EncryptAlgo == "" {
			e.EncryptAlgo = iocrypt.AlgoAES256CBC
		}
		e.encryptTool = iocrypt.Openssl{CryptCmd: e.EncryptCmd, EncryptElgo: e.EncryptAlgo, EncryptKey: e.passPhrase}
	} else if strings.Contains(e.EncryptCmd, "xbcrypt") {
		if e.EncryptAlgo == "" {
			e.EncryptAlgo = iocrypt.AlgoAES256
		}
		e.encryptTool = iocrypt.Xbcrypt{CryptCmd: e.EncryptCmd, EncryptElgo: e.EncryptAlgo, EncryptKey: e.passPhrase}
	} else {
		return errors.Errorf("unknown EncryptTool command: %s", e.EncryptCmd)
	}
	return nil
}

func (e *EncryptOpt) String() string {
	return fmt.Sprintf("EncryptOpt{Enable:%t, Cmd:%s, Algo:%s PublicKeyFile:%s encryptedKey:%s}",
		e.EncryptEnable, e.EncryptCmd, e.EncryptAlgo, e.EncryptPublicKey, e.encryptedPassPhrase)
}
