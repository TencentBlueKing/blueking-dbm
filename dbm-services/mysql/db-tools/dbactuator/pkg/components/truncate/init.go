package truncate

import "fmt"

func generateStageDBName(header, ts, dbName string) string {
	return fmt.Sprintf(
		`%s_%s_%s`,
		header,
		ts,
		dbName,
	)
}
