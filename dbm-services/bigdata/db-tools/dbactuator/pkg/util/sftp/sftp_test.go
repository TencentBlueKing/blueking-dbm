package sftp

import (
	"testing"
	"time"
)

func TestDownloadFile(t *testing.T) {
	config := Config{
		Username: "",
		Password: "", // required only if password authentication is to be used
		Server:   "127.0.0.1:36000",
		// KeyExchanges: []string{"diffie-hellman-group-exchange-sha256", "diffie-hellman-group14-sha256"}, // optional
		Timeout: time.Second * 10, // 0 for not timeout
	}

	Download(config, "/data/dbbak/", "/data/dbbak", "vip_VM-224-30-centos_127.0.0.1_20000_20220719_035743.info", 1)
}
