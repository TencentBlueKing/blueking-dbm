package definer

import (
	"fmt"
	"strings"

	"golang.org/x/exp/slices"
	"golang.org/x/exp/slog"
)

func checkDefiner(ownerFinger string, definer string) string {
	slog.Debug(
		"check definer",
		slog.String("owner", ownerFinger), slog.String("definer", definer),
	)

	splitDefiner := strings.Split(definer, `@`)
	definerUserName := splitDefiner[0]
	definerHost := splitDefiner[1]

	var msgSlice []string
	if slices.Index(mysqlUsers, definerUserName) < 0 {
		msgSlice = append(
			msgSlice,
			fmt.Sprintf("username %s not exists", definerUserName),
		)
	}
	if definerHost != "localhost" {
		msgSlice = append(
			msgSlice,
			fmt.Sprintf("host %s not localhost", definerHost),
		)
	}
	if len(msgSlice) > 0 {
		return fmt.Sprintf(
			"%s definer %s",
			ownerFinger,
			strings.Join(msgSlice, ","),
		)
	}
	return ""
}
