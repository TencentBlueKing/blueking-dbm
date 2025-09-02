package import_grants_file

import (
	"bufio"
	"crypto/md5"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/listener"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"

	"fmt"
	"os"
	"strings"
	"time"

	"github.com/antlr4-go/antlr/v4"
)

func (c *ImportGrantsFile) loadPrivFileToListeners(fp string) (privListeners []*listener.PrivListener, err error) {
	f, err := os.Open(fp)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = f.Close()
	}()

	doneChan := make(chan struct{})
	defer close(doneChan)
	counter := 0
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				logger.Info("%d priv sqls loaded", counter)
			case <-doneChan:
				logger.Info("%d priv sqls loaded", counter)
				return
			}
		}
	}()

	sqlMap := make(map[string]bool)
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()

		lineMd5 := fmt.Sprintf("%x", md5.Sum([]byte(line)))

		if !(strings.HasPrefix(strings.ToUpper(line), "GRANT") || strings.HasPrefix(strings.ToUpper(line), "CREATE")) {
			continue
		}

		in := antlr.NewInputStream(line)
		lexer := parsing.NewMariaDBLexer(in)
		stream := antlr.NewCommonTokenStream(lexer, 0)
		p := parsing.NewMariaDBParser(stream)
		tree := p.Root()

		l := listener.NewPrivListener(stream)
		antlr.ParseTreeWalkerDefault.Walk(l, tree)

		if _, ok := sqlMap[lineMd5]; !ok {
			sqlMap[lineMd5] = true
			privListeners = append(privListeners, l)
		} else {
			logger.Info("duplicate priv sql found: ", l.RawSQL)
		}

		counter++
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	doneChan <- struct{}{}

	return privListeners, nil
}
