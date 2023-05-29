package sftp

import (
	"testing"
	"time"
)

func TestDownloadFile(t *testing.T) {
	config := Config{
		Username: "mysql",
		Password: "xxx", // required only if password authentication is to be used
		Server:   "a.b.c.d:22",
		// KeyExchanges: []string{"diffie-hellman-group-exchange-sha256", "diffie-hellman-group14-sha256"}, // optional
		Timeout: time.Second * 10, // 0 for not timeout
	}

	Download(config, "/data/dbbak/", "/data/dbbak", "xxxx.info", 1)
}
