package pkg

import (
	"bufio"
	"os"

	"github.com/pkg/errors"
)

func ReadNginxProxyAddrs(fp string) (addrs []string, err error) {
	f, err := os.Open(fp)

	if err != nil {
		return nil, errors.Wrap(err, "failed to open nginx proxy addrs")
	}
	defer func() {
		_ = f.Close()
	}()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		addrs = append(addrs, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addrs")
	}
	return addrs, nil
}
