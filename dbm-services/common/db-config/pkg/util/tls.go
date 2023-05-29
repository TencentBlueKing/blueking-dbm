package util

import (
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"io/ioutil"
	"math/big"
)

// TLSInfo TODO
type TLSInfo struct {
	CertFile       string
	KeyFile        string
	CAFile         string
	TrustedCAFile  string
	ClientCertAuth bool

	// parseFunc exists to simplify testing. Typically, parseFunc
	// should be left nil. In that case, tls.X509KeyPair will be used.
	parseFunc func([]byte, []byte) (tls.Certificate, error)
}

// ClientConfig generates a tls.Config object for use by an HTTP client.
func (info TLSInfo) ClientConfig() (*tls.Config, error) {
	var cfg *tls.Config
	var err error

	if !info.Empty() {
		cfg, err = info.baseConfig()
		if err != nil {
			return nil, err
		}
	} else {
		cfg = &tls.Config{}
	}

	CAFiles := info.cafiles()
	if len(CAFiles) > 0 {
		cfg.RootCAs, err = newCertPool(CAFiles)
		if err != nil {
			return nil, err
		}
	}

	return cfg, nil
}

// newCertPool creates x509 certPool with provided CA files.
func newCertPool(CAFiles []string) (*x509.CertPool, error) {
	certPool := x509.NewCertPool()

	for _, CAFile := range CAFiles {
		pemByte, err := ioutil.ReadFile(CAFile)
		if err != nil {
			return nil, err
		}

		for {
			var block *pem.Block
			block, pemByte = pem.Decode(pemByte)
			if block == nil {
				break
			}
			cert, err := x509.ParseCertificate(block.Bytes)
			if err != nil {
				return nil, err
			}
			certPool.AddCert(cert)
		}
	}

	return certPool, nil
}

// String 用于打印
func (info TLSInfo) String() string {
	return fmt.Sprintf("cert = %s, key = %s, ca = %s, trusted-ca = %s, client-cert-auth = %v", info.CertFile, info.KeyFile,
		info.CAFile, info.TrustedCAFile, info.ClientCertAuth)
}

// Empty TODO
func (info TLSInfo) Empty() bool {
	return info.CertFile == "" && info.KeyFile == ""
}

func (info TLSInfo) baseConfig() (*tls.Config, error) {
	if info.KeyFile == "" || info.CertFile == "" {
		return nil, fmt.Errorf("KeyFile and CertFile must both be present[key: %v, cert: %v]", info.KeyFile, info.CertFile)
	}

	cert, err := ioutil.ReadFile(info.CertFile)
	if err != nil {
		return nil, err
	}

	key, err := ioutil.ReadFile(info.KeyFile)
	if err != nil {
		return nil, err
	}

	parseFunc := info.parseFunc
	if parseFunc == nil {
		parseFunc = tls.X509KeyPair
	}

	tlsCert, err := parseFunc(cert, key)
	if err != nil {
		return nil, err
	}

	cfg := &tls.Config{
		Certificates: []tls.Certificate{tlsCert},
		MinVersion:   tls.VersionTLS10,
	}
	return cfg, nil
}

// cafiles returns a list of CA file paths.
func (info TLSInfo) cafiles() []string {
	cs := make([]string, 0)
	if info.CAFile != "" {
		cs = append(cs, info.CAFile)
	}
	if info.TrustedCAFile != "" {
		cs = append(cs, info.TrustedCAFile)
	}
	return cs
}

// ======== BASE58
const (
	base58Table = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
)

func base58Hash(ba []byte) []byte {
	sha := sha256.New()
	sha2 := sha256.New() // hash twice
	ba = sha.Sum(ba)
	return sha2.Sum(ba)
}

// EncodeBase58 TODO
func EncodeBase58(ba []byte) []byte {
	if len(ba) == 0 {
		return nil
	}

	// Expected size increase from base58Table conversion is approximately 137%, use 138% to be safe
	ri := len(ba) * 138 / 100
	ra := make([]byte, ri+1)

	x := new(big.Int).SetBytes(ba) // ba is big-endian
	x.Abs(x)
	y := big.NewInt(58)
	m := new(big.Int)

	for x.Sign() > 0 {
		x, m = x.DivMod(x, y, m)
		ra[ri] = base58Table[int32(m.Int64())]
		ri--
	}

	// Leading zeroes encoded as base58Table zeros
	for i := 0; i < len(ba); i++ {
		if ba[i] != 0 {
			break
		}
		ra[ri] = '1'
		ri--
	}
	return ra[ri+1:]
}
