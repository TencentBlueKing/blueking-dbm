package listener

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/grant/import_grants_file/internal/parsing"
	"strings"
)

func (c *PrivListener) EnterTlsOption(ctx *parsing.TlsOptionContext) {
	c.TlsOptions = append(
		c.TlsOptions,
		strings.TrimSpace(c.tokenStream.GetTextFromInterval(ctx.GetSourceInterval())),
	)
}
