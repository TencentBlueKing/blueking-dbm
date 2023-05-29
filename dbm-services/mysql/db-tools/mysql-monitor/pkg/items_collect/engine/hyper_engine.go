package engine

import "strings"

func (c *Checker) hyperEngine() map[string]int {
	engineCount := make(map[string]int)
	for _, ele := range c.infos {
		engine := strings.ToLower(ele.Engine)
		if !strings.HasPrefix(engine, "myisam") {
			if _, ok := engineCount[engine]; !ok {
				engineCount[engine] = 0
			}
			engineCount[engine] += 1
		}
	}
	return engineCount
}
