package engine

import (
	"fmt"
	"strings"
)

func (c *Checker) myisam() (tables []string) {
	var myisamTables []string
	for _, ele := range c.infos {
		if strings.HasPrefix(strings.ToLower(ele.Engine), "myisam") {
			myisamTables = append(
				myisamTables,
				fmt.Sprintf("%s.%s", ele.TableSchema, ele.TableName),
			)
		}
	}
	return myisamTables
}
